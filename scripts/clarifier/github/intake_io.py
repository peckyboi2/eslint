"""Automatic issue workflow I/O with bounded internal artifacts. Serves B03–B06."""
import json
import os
from pathlib import Path
import time

from clarifier.controls import admission, intake_binding, intake_identity, policy as p
from clarifier.controls.state_store import StateStore
from clarifier.github import issue_io, workflow_io, intake_audit
from clarifier.github.github_api import GitHub
from clarifier.inference import hosted_runtime, hosted_transport, packages, pipeline, recording, request, staging, transport
from clarifier.outputs.validation import parse_json
from clarifier.shared import constants as c, intake_constants as k
from clarifier.shared.errors import ClarifierError, guarded


@guarded(p.IdentityError, 'Missing automatic trusted context')
def context(event: dict):
    """Return verified automatic context or raise before credential access."""
    fields=('event_name','repository','repository_id','repository_owner','repository_owner_id',
            'ref','ref_type','run_id','run_attempt','sha','workflow_sha','workflow_ref',
            'actor','actor_id','triggering_actor')
    data = {key:os.environ['GITHUB_'+key.upper()] for key in fields}
    return intake_identity.verify(data,event)


def platform(ctx, privileged: bool = False):
    """Return verified public/state edge or raise before privilege use."""
    if not privileged:
        api=GitHub(os.environ.get(k.READ_TOKEN_ENV)); api.verify_context(ctx)
        return api
    api=GitHub(); api.verify_context(ctx)
    token=os.environ.get('GH_TOKEN')
    if not token:
        raise p.PlatformError('Admission-scoped GitHub token unavailable')
    return GitHub(token)


def prepare_admission(ctx, api, snapshot, *, at: int) -> dict:
    """Persist actual-input quota then immutable binding or raise without inference."""
    binding=intake_binding.build(ctx,snapshot,workflow_io.fingerprint())
    admission.admit(StateStore(api,ctx),ctx,binding['input_key'],at)
    k.OUTPUT.mkdir(parents=True,exist_ok=True)
    recording.save_json(k.OUTPUT/k.BINDING_FILE,binding)
    return binding


def load_binding() -> dict:
    """Return bounded current-run binding or raise StagingError/ValidationError."""
    return parse_json(staging.read_safe(k.OUTPUT,k.BINDING_FILE,c.MAX_INPUT_BYTES).decode())


def begin_session(ctx, snapshot, binding: dict):
    """Return immutable dynamic run session or raise; no historical ledger mutation."""
    folder=k.OUTPUT/'preview'; folder.mkdir(parents=True,exist_ok=False)
    profile=hosted_runtime.load_profile(c.ROOT)
    config={**recording.load_configuration(c.ROOT/c.CONFIG_PATH),
            'version':k.VERSION,'source_issue':snapshot.number,'authentication':profile['authentication']}
    record=dict(run_id=ctx.run_id,started_at=recording.utc(),status='started',trigger='issues:opened',
                source_issue=snapshot.number,issue_id=snapshot.issue_id,input_hashes=snapshot.hashes,
                configuration_sha256=recording.record_configuration(folder),configuration_version=k.VERSION,
                engine=profile['engine'],model_requested=profile['model'],model_returned=c.UNKNOWN,
                engine_version=c.UNKNOWN,engine_binary_sha256=c.UNKNOWN,transport_request_attempts=0,
                skill_sha256=config['skill_sha256'],kind='hosted preview attempt',
                usage=c.UNKNOWN,cost=c.UNKNOWN,tool_calls=[],errors=[],public_actions=[],posting_available=False,
                verification_type='hosted attempt; completion required',inference_admitted=True,binding=binding)
    recording.save_json(folder/c.STARTED_FILE,record)
    return recording.Session(c.ROOT,folder,record,False,recording.utc,config)


def prepare_package(session, snapshot):
    """Return closed live package with no evaluator inputs or arbitrary support."""
    source=session.folder/'source'
    issue_io.write_source(snapshot,source)
    return packages.Package(snapshot.number,source,snapshot.hashes,
                            sum(map(len,snapshot.files.values())),dict(kind='issues:opened'))


def infer(ctx, api, opening: dict) -> int:
    """Run shared decision pipeline after fresh source/admission checks; errors stay internal."""
    snapshot=issue_io.collect(api,ctx,opening)
    binding=load_binding()
    intake_binding.validate(ctx,snapshot,workflow_io.fingerprint(),binding,StateStore(api,ctx).read().state)
    session=begin_session(ctx,snapshot,binding)
    try:
        staged=staging.prepare(session,prepare_package(session,snapshot))
        hosted_runtime.record_isolation(session)
        prompt=request.prepare(session,staged)
        recheck(ctx,api,opening,binding)
        pipeline.assess(session,staged,prompt,engine_setup=hosted_runtime.prepare_engine,
                        execute=checked_execution(ctx,api,opening,binding))
    except ClarifierError as error:
        recording.fail(session,error)
    finally:
        transport.close(session)
        staging.cleanup(session)
        recording.finish(session)
    return recording.report(session)


def recheck(ctx, api, opening: dict, binding: dict) -> None:
    """Raise before provider access if source, configuration or enabled state changed."""
    snapshot=issue_io.collect(api,ctx,opening)
    intake_binding.validate(ctx,snapshot,workflow_io.fingerprint(),binding,StateStore(api,ctx).read().state)


def checked_execution(ctx, api, opening: dict, binding: dict):
    """Return execution edge rechecking source/enabled after engine setup, before credentials."""
    def execute(session, staged, loaded, prompt, engine):
        recheck(ctx,api,opening,binding)
        hosted_transport.execute(session,staged,loaded,prompt,engine)
    return execute


def run_phase(phase: str, ctx, api, event: dict, snapshot) -> int:
    """Run one named phase or raise PlatformError for unexpected public operations."""
    if phase=='gate':
        return 0
    if phase=='admit':
        prepare_admission(ctx,api,snapshot,at=int(time.time()))
        return 0
    if phase=='infer':
        return infer(ctx,api,event['issue'])
    raise p.PlatformError('Automatic events permit preview phases only')


def run(phase: str) -> int:
    """Audit one automatic phase at a typed boundary; blocked work stays silent."""
    ctx=snapshot=None
    try:
        event=issue_io.read_event()
        ctx=context(event)
        api=platform(ctx,phase=='admit')
        snapshot=issue_io.collect(api,ctx,event['issue'])
        result=run_phase(phase,ctx,api,event,snapshot)
    except ClarifierError as error:
        intake_audit.write_phase(phase,ctx,snapshot,error)
        raise
    error=p.PlatformError('Inference incomplete; inspect retained preview record') if result else None
    intake_audit.write_phase(phase,ctx,snapshot,error)
    return result
