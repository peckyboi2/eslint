"""Trusted workflow context, manifests and artifacts for task 19."""
import hashlib
import json
import os
from pathlib import Path
import time

from clarifier.controls import admission
from clarifier.shared import constants as c
from clarifier.controls import identity
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.github.github_api import GitHub
from clarifier.inference.recording import save_json
from clarifier.controls.state_store import StateStore

OUTPUT = Path('evals/checks/workflow')


def context(workflow: str = p.TRIAGE_WORKFLOW) -> identity.Context:
    """Return verified GitHub context or raise IdentityError before reading tokens."""
    try:
        data = json.loads(os.environ['TRUSTED_GITHUB_CONTEXT'])
    except (KeyError, ValueError):
        raise p.IdentityError('Missing trusted GitHub context') from None
    return identity.verify(data, workflow)


def platform(ctx: identity.Context, privileged: bool = False) -> GitHub:
    """Return a live-verified edge; read job token only after tokenless checks."""
    public = GitHub()
    public.verify_context(ctx)
    if not privileged: return public
    token = os.environ.get('GH_TOKEN')
    if not token: raise p.PlatformError('Job-scoped token unavailable')
    return GitHub(token)


def fingerprint(root: Path = c.ROOT) -> dict:
    """Return source-only runtime/configuration identity, without source copies."""
    paths = [root/'scripts/clarifier'/name for name in c.SOURCE_PATHS]
    paths += list((root/'.github/workflows').glob('clarifier-*.yml'))
    paths += [root/c.CONFIG_PATH, root/c.SKILL_PATH, root/c.SCHEMA_PATH,
              root/'scripts/clarifier/config/hosted.json']
    files = {x.relative_to(root).as_posix(): hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(paths)}
    digest = hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(version=p.CONFIG_VERSION, aggregate_sha256=digest, source_hashes=files)


def dispatch_mode() -> str:
    """Return the trusted dispatch mode or raise PostingBlocked for unknown values."""
    value = os.environ.get('DISPATCH_MODE', 'preview')
    if value not in ('preview', 'post'): raise p.PostingBlocked('Unknown dispatch mode')
    return value


def prepare_admission(ctx, api) -> dict:
    """Reserve one fixed report before inference and preserve its trusted binding."""
    key = admission.input_key(c.APPROVED)
    state = admission.admit(StateStore(api, ctx), ctx, key, int(time.time()))
    record = dict(run_id=ctx.run_id, attempt=ctx.attempt, sha=ctx.sha, input_key=key,
                  event_key=admission.event_key(ctx,key), source_issue=c.SOURCE_ISSUE,
                  mode=dispatch_mode(), configuration=fingerprint(), public_actions=[])
    OUTPUT.mkdir(parents=True,exist_ok=True)
    save_json(OUTPUT/'admission.json', record)
    return record


def validate_binding(ctx, binding: dict, state: dict) -> None:
    """Reject swapped artifacts or missing quota before inference/posting."""
    key = admission.input_key(c.APPROVED)
    expected = dict(run_id=ctx.run_id, attempt=ctx.attempt, sha=ctx.sha, input_key=key,
                    event_key=admission.event_key(ctx,key), source_issue=c.SOURCE_ISSUE,
                    mode=dispatch_mode(), configuration=fingerprint(), public_actions=[])
    if binding != expected: raise p.AdmissionDenied('Admission artifact identity mismatch')
    if not ledger.validate(state)['enabled']: raise p.AdmissionDenied('Admission disabled')
    if not any(a['run_id']==ctx.run_id and a['input_key']==key and a['event_key']==expected['event_key'] for a in state['admissions']):
        raise p.AdmissionDenied('Persisted admission missing')


def load_binding() -> dict:
    """Return deterministic artifact JSON or raise AdmissionDenied."""
    from clarifier.outputs.validation import parse_json
    try:
        path = OUTPUT/'admission.json'
        if path.stat().st_size > c.MAX_INPUT_BYTES: raise p.AdmissionDenied('Admission artifact oversized')
        return parse_json(path.read_text())
    except OSError:
        raise p.AdmissionDenied('Admission artifact unavailable') from None


def infer(ctx, api, binding: dict) -> int:
    """Run existing no-tool adapter after fresh gates; preserve a workflow envelope."""
    from clarifier import preview
    validate_binding(ctx,binding,StateStore(api,ctx).read().state)
    result = preview.run()
    save_json(OUTPUT/'inference-status.json', dict(exit_code=result,run_id=ctx.run_id,
              configuration=fingerprint(),verification_type='platform attempt',public_actions=[]))
    return result
