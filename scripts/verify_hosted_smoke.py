"""Replay saved hosted-smoke evidence offline; never invoke a provider. Serves H02."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess

FOLDER=Path('evals/hosted-v11/live-smoke-artifacts-v2-20261029')
ASSESSMENT=FOLDER/'assessment.json'
MAX_FILES=256
MAX_FILE_BYTES=2097152
MAX_TOTAL_BYTES=33554432
REPOSITORY='peckyboi2/eslint'
REPOSITORY_ID=1435519573
ATTACK_FIXTURE='scripts/clarifier/tests/fixtures/attacks-v1.json'
SKILL='.claude/skills/eslint-clarification/SKILL.md'


def require(value: bool, reason: str) -> None:
    """Raise ValueError when saved integration evidence is inconsistent or incomplete."""
    if not value:
        raise ValueError('Hosted smoke: '+reason)


def digest(data: bytes) -> str:
    """Return the exact content SHA-256 without side effects."""
    return hashlib.sha256(data).hexdigest()


def read(root: Path, name: str | Path) -> bytes:
    """Return bounded regular evidence bytes; reject missing paths, symlinks and escapes."""
    name=Path(name)
    require(not name.is_absolute() and '..' not in name.parts,'unsafe evidence path')
    path=root/name
    require(not any(p.is_symlink() for p in (path,*path.parents)),'symlink in evidence')
    require(path.is_file() and path.stat().st_size<=MAX_FILE_BYTES,'missing/oversized evidence: '+str(name))
    return path.read_bytes()


def load(root: Path, name: str | Path):
    """Return bounded saved JSON; malformed input raises ValueError."""
    return json.loads(read(root,name))


def verify_inventory(root: Path, folder: Path, manifest: dict) -> None:
    """Verify an exact bounded folder inventory; missing hidden files raise ValueError."""
    require(isinstance(manifest,dict) and 0<len(manifest)<=MAX_FILES,'invalid inventory size')
    actual={p.relative_to(root/folder).as_posix() for p in (root/folder).rglob('*') if p.is_file()}
    require(actual==set(manifest)|{'SHA256-MANIFEST.json'},'folder inventory differs')
    total=0
    for name,expected in manifest.items():
        data=read(root,folder/name)
        require(isinstance(expected,str) and re.fullmatch('[a-f0-9]{64}',expected) is not None,'invalid digest')
        require(digest(data)==expected,'artifact hash mismatch: '+name)
        total+=len(data)
    require(total<=MAX_TOTAL_BYTES,'evidence exceeds total byte bound')


def verify_identity(summary: dict, run: dict, issue: dict, record: dict) -> None:
    """Bind issue opening, successful workflow, source commit and recorded preview."""
    commit=summary['code_commit']; run_id=summary['run_id']
    require(isinstance(commit,str) and re.fullmatch('[a-f0-9]{40}',commit) is not None,'invalid source commit')
    require(isinstance(run_id,str) and run_id.isdecimal() and int(run_id)>0,'invalid run identity')
    require(summary['repository']==REPOSITORY and summary['repository_id']==REPOSITORY_ID,'wrong repository')
    require(run['repository']['id']==REPOSITORY_ID and run['repository']['full_name']==REPOSITORY,'run repository differs')
    require(run['id']==int(run_id) and run['head_sha']==commit and run['event']=='issues'
            and run['run_attempt']==1 and run['conclusion']=='success' and run['status']=='completed','workflow receipt differs')
    require(run['path']=='.github/workflows/clarifier-triage.yml' and run['head_branch']=='main','untrusted workflow/ref')
    require(issue['id']==record['issue_id']==summary['issue_id'] and issue['number']==record['source_issue']==summary['issue_number'],
            'issue target differs')
    require(record['run_id']==run_id and record['trigger']=='issues:opened' and record['binding']['sha']==commit,'record origin differs')
    require(record['binding']['run_id']==run_id and record['binding']['issue_id']==issue['id']
            and record['binding']['source_issue']==issue['number'] and record['binding']['repository_id']==REPOSITORY_ID,
            'admission target differs')
    require(summary['run_url']==f'https://github.com/{REPOSITORY}/actions/runs/{run_id}'
            and summary['issue_url']==f'https://github.com/{REPOSITORY}/issues/{issue["number"]}','receipt URL differs')


def verify_source_commit(root: Path, commit: str, sources: dict) -> None:
    """Check every recorded runtime hash against immutable local Git blobs, offline."""
    require(0<len(sources)<=128,'invalid runtime inventory')
    for name,expected in sources.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\n' not in name,'unsafe source path')
        data=subprocess.check_output(['git','show',commit+':'+name],cwd=root,timeout=10)
        require(len(data)<=MAX_FILE_BYTES and digest(data)==expected,'source commit bytes differ: '+name)


def aggregate(sources: dict) -> str:
    """Return the recorder's deterministic configuration digest."""
    return digest(json.dumps(sources,sort_keys=True,separators=(',',':')).encode())


def verify_configuration(root: Path, folder: Path, summary: dict, record: dict, expected: dict) -> None:
    """Check full recorder identity and the separate admission identity without conflating them."""
    saved=load(root,folder/'configuration-hashes.json')
    require(not set(saved['files'])&set(saved['source_hashes']),'overlapping retained/source identities')
    sources=saved['files']|saved['source_hashes']
    require(sources==expected['source_hashes'] and aggregate(sources)==saved['aggregate_sha256']
            ==expected['aggregate_sha256']==record['configuration_sha256']==summary['configuration_sha256'],
            'current runtime aggregate differs')
    require(record['configuration_version']==summary['configuration_version']==expected['version'],'current source version differs')
    binding=record['binding']['configuration']
    require(binding['source_hashes']=={k:v for k,v in sources.items() if k!=ATTACK_FIXTURE}
            and aggregate(binding['source_hashes'])==binding['aggregate_sha256']==summary['binding_configuration_sha256']
            and binding['version']==expected['version'],'admission configuration differs')
    for name,expected_sha in saved['files'].items():
        require(digest(read(root,folder/'configuration'/name))==expected_sha,'retained instruction/settings differs')
    verify_source_commit(root,summary['code_commit'],sources)


def verify_original_preview(root: Path, folder: Path, summary: dict) -> None:
    """Check every original preview file, including the canonical hidden skill, without recovery."""
    validation=summary['artifact_validation']
    require(summary['artifact_completeness_status']=='passed' and validation['missing_original_files']==[]
            and validation['mismatched_original_files']==[] and validation['original_artifacts_modified'] is False,
            'original artifact export is incomplete')
    manifest=load(root,folder/'artifact-hashes.json')
    require(0<len(manifest)<=MAX_FILES and len(manifest)==validation['manifest_entries']==validation['verified_original_files'],
            'original preview count differs')
    require('configuration/'+SKILL in manifest,'canonical hidden skill absent from original inventory')
    copied=load(root,FOLDER/'original-copy-sha256.json')
    for name,expected in manifest.items():
        path=folder/name
        require(digest(read(root,path))==expected,'missing/changed original preview: '+name)
        require(copied[path.relative_to(FOLDER).as_posix()]==expected,'original-copy provenance differs')
    read(root,folder/'configuration'/SKILL)


def verify_model(root: Path, folder: Path, summary: dict, record: dict) -> None:
    """Replay tool rejection, actual output, model/usage and native skill-load checks."""
    from clarifier.inference.transport import inspect_response
    from clarifier.outputs.validation import parse_and_validate
    request=load(root,folder/'request.json'); loader=load(root,folder/'loader.json')
    completion,text=inspect_response(read(root,folder/'response.sse'))
    require(record['status']=='completed' and record['engine_exit_code']==0 and record['errors']==[],'preview did not complete')
    require(record['transport_request_attempts']==summary['provider_requests']==1,'provider request count differs')
    require(record['model_requested']==record['model_returned']==summary['model_requested']==summary['model_returned']
            ==request['model']==completion['model']=='gpt-6.1-sol','requested/returned model differs')
    require(request['tools']==[] and request['tool_choice']=='none' and record['tool_calls']==summary['tool_calls']==[],
            'unexpected model capability/action')
    require(record['usage']==summary['usage']==completion['usage'],'usage evidence differs')
    require(load(root,folder/'provider-status.json')['status']==summary['provider_status']==200,'provider did not succeed')
    require(read(root,folder/'raw-output.txt').decode()==text,'raw provider output differs')
    require(load(root,folder/'validation.json')['validated_output']==parse_and_validate(text),'validated output differs')
    canonical=read(root,folder/'configuration'/SKILL)
    require(loader['native_prompt_matched'] is True and loader['implicit_host_context_forwarded'] is False
            and loader['outbound_tools']==[] and loader['loaded_content_sha256']==digest(canonical.decode().strip().encode())
            and loader['canonical_content_sha256']==record['skill_sha256']==digest(canonical),'native skill proof differs')


def verify_silence(root: Path, summary: dict, record: dict, issue: dict) -> None:
    """Check saved GitHub silence and admission receipts; no network requests are made."""
    require(record['public_actions']==record['binding']['public_actions']==summary['public_actions']==[]
            and record['posting_available'] is False and issue['comments']==summary['issue_comments_observed']==0,
            'unexpected public output')
    require(load(root,FOLDER/'metadata/comments-final.json')==[],'comments receipt is not silent')
    envelope=load(root,FOLDER/'metadata/state-final.json')
    state=json.loads(base64.b64decode(envelope['content'],validate=False))
    require(state['posting_enabled'] is False and state['posts']==[],'public posting was enabled')
    binding=record['binding']
    matched=[row for row in state['admissions'] if row['run_id']==record['run_id']]
    require(len(matched)==1 and all(matched[0][key]==binding[key] for key in ('input_key','event_key')),
            'persisted admission receipt differs')


def verify(root: Path, reference: dict, configuration: dict) -> dict:
    """Return one verified current integration smoke; no accuracy evaluation is inferred."""
    require(reference['assessment']==ASSESSMENT.as_posix(),'unexpected current-smoke assessment path')
    require(digest(read(root,ASSESSMENT))==reference['sha256'],'assessment review hash differs')
    summary=load(root,ASSESSMENT)
    verify_inventory(root,FOLDER,load(root,FOLDER/'SHA256-MANIFEST.json'))
    record_folder=FOLDER/'artifacts'/('preview-'+summary['run_id'])/'preview'
    record=load(root,record_folder/'record.json')
    run=load(root,FOLDER/'metadata/run-final.json'); issue=load(root,FOLDER/'metadata/issue-final.json')
    verify_identity(summary,run,issue,record)
    verify_original_preview(root,record_folder,summary)
    verify_configuration(root,record_folder,summary,record,configuration)
    verify_model(root,record_folder,summary,record)
    verify_silence(root,summary,record,issue)
    require(summary['integration_status']=='passed' and summary['semantic_correctness_status']=='not_scored',
            'integration smoke was relabelled as accuracy evaluation')
    return dict(run_id=summary['run_id'],source_commit=summary['code_commit'],configuration_sha256=summary['configuration_sha256'],
                provider_calls=1,public_actions=0,artifact_completeness='passed',evaluated=False,
                requested_model=summary['model_requested'],returned_model=summary['model_returned'],
                verification='Offline replay of saved hosted integration evidence; no new requests or semantic scoring')
