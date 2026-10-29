#!/usr/bin/env python3
"""Verify the active candidate separately from retained v9/v10 evidence. Serves C04/H01."""
import argparse
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
FOLDER=Path('evals/automatic-v10')
BASELINE_COMMIT='7fdbf7322cbecbe852ce971b6c10f343daa1aaf0'
CANDIDATE=FOLDER/'candidate.json'
OVERLAY=FOLDER/'baseline-overlay'
HOSTED_FOLDER=Path('evals/hosted-v11')
HOSTED_CANDIDATE=HOSTED_FOLDER/'candidate.json'
HOSTED_PRESERVATION=HOSTED_FOLDER/'preservation.json'
PRESERVATION_SHA256='0639f8a750f03327a567a24a282fad2596671872c50227b3488e79c16a7398ac'
LEGACY_VERSION='automatic-preview-v10'
HOSTED_VERSION='hosted-preview-v11'
MUTABLE_DOCS={'DESIGN.md','SUBMISSION.md','evals/README.md','evals/golden/INDEX.md'}


def require(value: bool, reason: str) -> None:
    """Raise ValueError on a missing evidence invariant."""
    if not value:
        raise ValueError(reason)


def sha(data: bytes) -> str:
    """Return content SHA-256 with no side effects."""
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    """Return saved JSON or raise for malformed/missing content."""
    return json.loads(path.read_text())


def git_bytes(root: Path, name: str) -> bytes:
    """Return baseline Git blob or raise; no remote/network access."""
    return baseline_blobs(root)[name]


@lru_cache(maxsize=3)
def baseline_blobs(root: Path) -> dict[str,bytes]:
    """Read retained immutable Git blobs in one bounded batch or raise on missing objects."""
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE_COMMIT],cwd=root,text=True).splitlines()
    commands=''.join(BASELINE_COMMIT+':'+name+'\n' for name in names).encode()
    raw=subprocess.run(['git','cat-file','--batch'],cwd=root,input=commands,check=True,capture_output=True).stdout
    files={}; offset=0
    for name in names:
        end=raw.index(b'\n',offset)
        header=raw[offset:end].split()
        require(len(header)==3 and header[1]==b'blob','Baseline blob unavailable')
        size=int(header[2]); offset=end+1
        files[name]=raw[offset:offset+size]; offset+=size+1
    return files


def safe_file(root: Path, name: str) -> Path:
    """Return safe regular path or raise ValueError on symlinks/escape/missing files."""
    path=root/name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe verification path')
    require(not any(item.is_symlink() for item in (path,*path.parents)),'Symlink in candidate/evidence')
    require(path.is_file(),'Missing candidate/evidence: '+name)
    return path


def verify_originals(root: Path, candidate: dict) -> int:
    """Verify retained Git/evidence and original uncommitted overlay or raise ValueError."""
    baseline=read_json(root/FOLDER/'baseline.json')
    require(baseline['baseline_commit']==BASELINE_COMMIT,'Baseline commit changed')
    overlay=read_json(root/OVERLAY/'SHA256-MANIFEST.json')
    for name,digest in overlay.items():
        require(sha(safe_file(root,(OVERLAY/name).as_posix()).read_bytes())==digest,'Preexisting overlay changed')
        if name in baseline['preexisting_worktree']:
            require(digest==baseline['preexisting_worktree'][name],'Preexisting work not preserved')
        if name not in candidate['files']:
            require(sha(safe_file(root,name).read_bytes())==digest,'Unchanged preexisting file changed: '+name)
    frozen=read_json(root/'evals/checks/gate-f-20261028/freeze.json')
    for name,digest in frozen['files'].items():
        require(sha(git_bytes(root,name))==digest,'Retained v9 Git blob mismatch: '+name)
        require(name in candidate['files'] or sha(safe_file(root,name).read_bytes())==digest,
                'Unexpected frozen evidence change: '+name)
    for name,digest in baseline['preserved_evidence'].items():
        path=(OVERLAY/name).as_posix() if name in MUTABLE_DOCS else name
        require(sha(safe_file(root,path).read_bytes())==digest,'Earlier evidence changed: '+name)
    return len(frozen['files'])


def candidate_path(root: Path) -> Path:
    """Return the active manifest path; incomplete v11 preparation never falls back to v10."""
    return HOSTED_CANDIDATE if (root/HOSTED_FOLDER).exists() else CANDIDATE


def verify_tree(root: Path, candidate: dict) -> int:
    """Verify every original/current path, including ignored extras; raises on drift."""
    import verify_submission as old
    verify_candidate_scope(candidate)
    actual=old.tree_files(root)
    original=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE_COMMIT],cwd=root,text=True).splitlines())
    baseline=read_json(root/FOLDER/'baseline.json')
    prior=set(baseline['preserved_evidence'])|{'scripts/check_v9_attacks.py'}
    allowed=original|prior|set(candidate['files'])|{candidate_path(root).as_posix()}
    require(actual==allowed,'Current tree missing/unlisted paths: '+str(sorted(actual^allowed)))
    for name in original-set(candidate['files']):
        require(safe_file(root,name).read_bytes()==git_bytes(root,name),'Original noncandidate file changed: '+name)
    for name,digest in candidate['files'].items():
        require(sha(safe_file(root,name).read_bytes())==digest,'Candidate hash mismatch: '+name)
    old.check_links(root)
    return len(actual)


def verify_candidate_scope(candidate: dict) -> None:
    """Raise ValueError if candidate bytes change inherited code/workflows or old evidence."""
    permitted=MUTABLE_DOCS|{'.gitattributes','scripts/verify_submission.py','scripts/verify_automatic.py',
        'scripts/check_v9_attacks.py','scripts/evaluate_automatic.py','scripts/submission_tests/test_verify_submission.py',
        'evals/golden/final-results-v9/README.md'}
    prefixes=('scripts/clarifier/','scripts/automatic_tests/','evals/automatic-v10/')
    if candidate['version']==HOSTED_VERSION:
        prefixes+=('evals/hosted-v11/',)
    workflows={'.github/workflows/clarifier-'+name+'.yml' for name in ('triage','stop','approve')}
    require(all(name in permitted|workflows or name.startswith(prefixes) for name in candidate['files']),
            'Candidate scope includes inherited source/workflows or earlier evidence')


def verify_preserved_v10(root: Path, candidate: dict) -> dict:
    """Verify all superseded v10 metadata and consumed reservation bytes or raise ValueError."""
    raw=safe_file(root,HOSTED_PRESERVATION.as_posix()).read_bytes()
    require(sha(raw)==PRESERVATION_SHA256,'Prior v10 preservation inventory changed')
    preserved=json.loads(raw)
    actual={path.relative_to(root).as_posix() for path in (root/FOLDER).rglob('*') if path.is_file()}
    require(actual==set(preserved['files']),'Prior v10 evidence inventory differs')
    for name,digest in preserved['files'].items():
        require(sha(safe_file(root,name).read_bytes())==digest,'Prior v10 evidence changed: '+name)
    require(candidate['supersedes']==dict(path=CANDIDATE.as_posix(),
            sha256=preserved['files'][CANDIDATE.as_posix()]),'Superseded candidate identity differs')
    budget=preserved['consumed_reservations']
    require(budget['previous']==51 and budget['supplemental']==3 and budget['total']==54
            and budget['reused_or_refunded'] is False,'Historical allowance was reset')
    for name,digest in budget['files'].items():
        require(sha(safe_file(root,name).read_bytes())==digest,'Consumed reservation changed: '+name)
    return dict(candidate_sha256=preserved['files'][CANDIDATE.as_posix()],
                evaluation_freeze_sha256=preserved['files'][(FOLDER/'evaluation-freeze.json').as_posix()],
                preserved_metadata_files=len(actual),previous_reservations_unchanged=54,
                status='Superseded local candidate/proposed freeze; not evaluated or reclassified as hosted',
                source_reconstruction=preserved['prior_active_file_hash_reference'])


def verify_hosted_configuration(root: Path, candidate: dict) -> None:
    """Bind every current runtime source and settings byte to the new candidate or raise ValueError."""
    from clarifier.inference.recording import load_configuration
    from clarifier.shared import constants as c
    config=load_configuration(root/c.CONFIG_PATH)
    declared=candidate['configuration']
    require(candidate['version']==declared['version']==config['version']==HOSTED_VERSION,
            'Hosted candidate/configuration version differs')
    sources={name.as_posix():sha(safe_file(root,name.as_posix()).read_bytes()) for name in c.CONFIG_PATHS}
    require(declared['source_hashes']==sources,'Hosted runtime/configuration inventory differs')
    require(declared['aggregate_sha256']==sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()),
            'Hosted configuration aggregate differs')
    require(type(candidate['provider_calls']) is int and candidate['provider_calls']==0
            and type(candidate['public_actions']) is int and candidate['public_actions']==0
            and candidate['evaluated'] is False and candidate['hosted_execution_verified'] is False,
            'Preparation manifest cannot claim provider calls or public writes')


@contextmanager
def historical_projection(root: Path):
    """Materialize exact v9 Git plus one preexisting overlay for offline historical checks."""
    with tempfile.TemporaryDirectory(prefix='cs467-v9-baseline-',dir='/private/tmp') as folder:
        target=Path(folder)/'v9'
        subprocess.run(['git','clone','--shared','--no-checkout','--quiet',str(root),str(target)],check=True,capture_output=True)
        subprocess.run(['git','checkout','--quiet','--detach',BASELINE_COMMIT],cwd=target,check=True,capture_output=True)
        subprocess.run(['git','remote','set-url','origin','https://github.com/peckyboi2/eslint.git'],cwd=target,check=True,capture_output=True)
        for name in read_json(root/OVERLAY/'SHA256-MANIFEST.json'):
            shutil.copyfile(root/OVERLAY/name,target/name)
        supplement=Path('evals/golden/adversarial-v9-20261029')
        shutil.copytree(root/supplement,target/supplement)
        yield target


def run_historical(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    """Return original verifier result on retained v9 bytes; never invoke inference."""
    with historical_projection(root) as target:
        return subprocess.run([sys.executable,'-B',str(target/'scripts/verify_submission.py'),*arguments],
                              cwd=target,capture_output=True,text=True,timeout=120)


def verify_candidate(root: Path, expected_sha256: str | None) -> dict:
    """Return separately labelled historical/current verification or raise on byte/tree mismatch."""
    manifest=candidate_path(root)
    raw=safe_file(root,manifest.as_posix()).read_bytes()
    require(expected_sha256 is None or sha(raw)==expected_sha256,'Candidate review hash differs')
    candidate=json.loads(raw)
    hosted=manifest==HOSTED_CANDIDATE
    require(candidate['version']==(HOSTED_VERSION if hosted else LEGACY_VERSION),'Candidate version differs')
    require(candidate['baseline_commit']==BASELINE_COMMIT,'Candidate baseline commit differs')
    prior=verify_preserved_v10(root,candidate) if hosted else None
    frozen=verify_originals(root,candidate)
    files=verify_tree(root,candidate)
    if hosted:
        verify_hosted_configuration(root,candidate)
    historical=run_historical(root)
    require(historical.returncode==0,'Historical v9 verifier failed: '+historical.stderr)
    result=json.loads(historical.stdout)
    result['historical_design_lines']=result['design_lines']
    result['design_lines']=len((root/'DESIGN.md').read_text().splitlines())
    from clarifier.github import workflow_audit
    result.update(verification='Current '+candidate['version']+' tree plus exact retained Git/overlay v9 replay; offline',
                  current_candidate=dict(version=candidate['version'],manifest_path=manifest.as_posix(),manifest_sha256=sha(raw),
                    identified_files=len(candidate['files']),whole_tree_files=files,
                    model_calls=0,evaluated=False,hosted=False,capabilities=workflow_audit.run(root)),
                  v9_baseline=dict(commit=BASELINE_COMMIT,frozen_git_files=frozen,
                    overlay='One snapshot preserves preexisting uncommitted verifier/docs; not active runtime copies'))
    if prior is not None:
        result['v10_preserved']=prior
    return result


def verify(root: Path=ROOT, expected_sha256: str | None=None) -> dict:
    """Return verified evidence or raise ValueError for malformed or missing metadata."""
    try:
        return verify_candidate(root,expected_sha256)
    except (KeyError,TypeError,OSError,subprocess.SubprocessError):
        raise ValueError('Malformed or unavailable automatic/baseline verification metadata') from None


def main() -> int:
    """Return offline verification/test exit code; no provider access."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--tests',action='store_true',help='Run current candidate safety tests in a disposable copy')
    args=parser.parse_args()
    try:
        result=verify(ROOT,args.candidate_sha256)
        if args.tests:
            import verify_submission as old
            with old.disposable_copy(ROOT) as target:
                return subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',
                    'scripts/clarifier/tests','-t','scripts','-p','test_*.py','-v'],cwd=target).returncode
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        print('FAIL: '+str(error),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
