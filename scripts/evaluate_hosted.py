#!/usr/bin/env python3
"""Owner-only frozen historical evaluation through the existing hosted pipeline."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from clarifier.controls import admission, identity, policy as p
from clarifier.controls.state_store import StateStore, transact
from clarifier.github.github_api import GitHub
from clarifier.inference import adversarial, hosted_runtime, hosted_transport, packages, pipeline, recording, request, staging, transport
from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError, ConfigurationError

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW='clarifier-evaluate.yml'
FOLDER=Path('evals/hosted-v11/campaign-20261029')
OUTPUT=Path('evals/hosted-evaluation-workflow')
LIMIT=13
EVALUATION_WINDOW=60


def require(condition: bool, message: str) -> None:
    """Reject an inconsistent trusted evaluation boundary before inference."""
    if not condition:
        raise ConfigurationError(message)


def load_json(path: Path) -> dict:
    """Read bounded regular JSON using the existing safe path checks."""
    from clarifier.outputs.validation import parse_json
    return parse_json(staging.read_safe(path.parent,path.name,c.MAX_RESPONSE_BYTES).decode())


def context(data: dict) -> identity.Context:
    """Accept only the owner, exact sandbox/main workflow and original dispatch."""
    expected={'event_name':'workflow_dispatch','repository':p.REPOSITORY,
              'repository_id':str(p.REPOSITORY_ID),'repository_owner':p.OWNER,
              'repository_owner_id':str(p.OWNER_ID),'actor':p.OWNER,'actor_id':str(p.OWNER_ID),
              'triggering_actor':p.OWNER,'ref':p.TRUSTED_REF,'ref_type':'branch',
              'workflow_ref':f'{p.REPOSITORY}/.github/workflows/{WORKFLOW}@{p.TRUSTED_REF}'}
    require(all(data.get(key)==value for key,value in expected.items()),'Untrusted evaluation trigger/identity/ref')
    require(data.get('run_attempt')==1 or data.get('run_attempt')=='1','Evaluation reruns are forbidden')
    sha=str(data.get('sha','')); run=str(data.get('run_id',''))
    require(re.fullmatch(p.GIT_SHA_PATTERN,sha) is not None and data.get('workflow_sha')==sha,'Evaluation workflow/code SHA differs')
    require(re.fullmatch(p.RUN_PATTERN,run) is not None,'Invalid evaluation run identity')
    return identity.Context(run,1,sha,WORKFLOW)


def reviewed(root: Path, expected_freeze: str) -> tuple[dict,dict]:
    """Verify owner approval, exact frozen source and all predeclared case slots."""
    frozen_raw=staging.read_safe(root,(FOLDER/'freeze.json').as_posix(),c.MAX_RESPONSE_BYTES)
    require(recording.sha(frozen_raw)==expected_freeze,'Evaluation freeze digest differs')
    frozen=json.loads(frozen_raw)
    plan=load_json(root/FOLDER/'plan.json'); approval=load_json(root/FOLDER/'approval.json')
    plan_sha=recording.sha((root/FOLDER/'plan.json').read_bytes())
    require(frozen['plan_sha256']==plan_sha,'Evaluation plan changed after freeze')
    rows=plan['cases']
    require(plan['attempt_limit']==LIMIT and plan['retries']==0 and plan['posting'] is False,'Evaluation allowance changed')
    require(plan['temporary_rolling_window_seconds']==EVALUATION_WINDOW,'Temporary evaluation window changed')
    require(len(rows)==LIMIT and [row['slot'] for row in rows]==list(range(1,LIMIT+1)),'Evaluation slots changed')
    require([row['issue'] for row in rows[:10]]==list(c.HISTORICAL_CASE_IDS),'Historical order changed')
    require([row['attack'] for row in rows[10:]]==list(adversarial.ATTACK_IDS),'Attack order changed')
    require([row['kind'] for row in rows]==['historical']*10+['attack']*3,'Evaluation kinds changed')
    require(all(row['issue']==c.SOURCE_ISSUE for row in rows[10:]),'Attack source issue changed')
    require([row['expected_decision'] for row in rows]==['clarify','clarify','human_review']+['no_action']*7+['clarify']*3,'Original expectations changed')
    require(len({row['run_id'] for row in rows})==LIMIT,'Duplicate evaluation run IDs')
    expected=dict(owner_id=p.OWNER_ID,campaign_id=plan['campaign_id'],plan_sha256=plan_sha,
                  freeze_sha256=expected_freeze,attempt_limit=LIMIT,allow_provider_calls=True,posting=False,
                  temporary_rolling_window_seconds=EVALUATION_WINDOW)
    require(all(type(approval.get(key)) is type(value) and approval[key]==value for key,value in expected.items()),'Owner approval does not bind the fixed evaluation')
    require(isinstance(approval.get('authorization_text'),str) and bool(approval['authorization_text'].strip()),'Missing direct owner authorization')
    required={name.as_posix() for name in c.CONFIG_PATHS}|{'scripts/evaluate_hosted.py',f'.github/workflows/{WORKFLOW}',(FOLDER/'plan.json').as_posix()}
    required|={f'evals/golden/prepared-inputs/inputs/{row["issue"]}/{name}' for row in rows[:10] for name in row['input_hashes']}
    require(required<=set(frozen['files']),'Evaluation freeze omits required source/input files')
    for name,digest in frozen['files'].items():
        require(recording.sha(staging.read_safe(root,name,c.MAX_RESPONSE_BYTES))==digest,'Frozen evaluation source/input changed: '+name)
    runtime={name.as_posix():frozen['files'][name.as_posix()] for name in c.CONFIG_PATHS}
    require(recording.sha(json.dumps(runtime,sort_keys=True,separators=(',',':')).encode())==frozen['configuration_sha256'],'Frozen runtime aggregate differs')
    return plan,frozen


def slot_key(plan: dict, row: dict) -> str:
    """Bind a lifetime evaluation slot independently of new GitHub dispatch IDs."""
    value=dict(campaign_id=plan['campaign_id'],slot=row['slot'],inputs=row['input_hashes'])
    return recording.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())


def reserve(state: dict, ctx, plan: dict, row: dict, at: int) -> dict:
    """Reserve one slot with an explicitly approved evaluation-only short window."""
    keys=[slot_key(plan,item) for item in plan['cases']]
    require(state['posting_enabled'] is False,'Evaluation requires posting disabled')
    used={item['input_key'] for item in state['admissions']}
    require(all(key in used for key in keys[:row['slot']-1]),'Earlier evaluation slot not reserved')
    require(not any(key in used for key in keys[row['slot']-1:]),'Evaluation slot already consumed or order changed')
    window=plan.get('active_rolling_window_seconds',p.ROLLING_SECONDS)
    require(window in (EVALUATION_WINDOW,86400),'Unapproved evaluation window')
    original=p.ROLLING_SECONDS
    try:
        # This single-threaded admission process alone uses the temporary window.
        # The shared module/source, automatic workflow and durable history stay intact.
        p.ROLLING_SECONDS=window
        return admission.reserve(state,ctx,keys[row['slot']-1],at)
    finally:
        p.ROLLING_SECONDS=original


def binding(ctx, plan: dict, row: dict, freeze_sha: str) -> dict:
    """Return exact same-run admission envelope without granting public output."""
    key=slot_key(plan,row)
    return dict(campaign_id=plan['campaign_id'],slot=row['slot'],run_id=ctx.run_id,attempt=1,
                code_sha=ctx.sha,freeze_sha256=freeze_sha,input_key=key,event_key=admission.event_key(ctx,key),
                input_hashes=row['input_hashes'],rolling_window_seconds=plan.get('active_rolling_window_seconds',86400),
                rolling_limit=p.ROLLING_LIMIT,campaign_limit=p.CAMPAIGN_LIMIT,public_actions=[])


def verify_reservation(state: dict, ctx, plan: dict, row: dict, freeze_sha: str, saved: dict) -> None:
    """Reject swapped artifacts, disabled state or missing durable quota."""
    wanted=binding(ctx,plan,row,freeze_sha)
    require(saved==wanted,'Evaluation admission artifact differs')
    require(state['enabled'] is True and state['posting_enabled'] is False,'Evaluation disabled or posting enabled')
    require(any(all(item[key]==wanted[key] for key in ('run_id','event_key','input_key'))
                for item in state['admissions']),'Durable evaluation reservation missing')


def infer(root: Path, ctx, api, plan: dict, frozen: dict, row: dict, freeze_sha: str) -> int:
    """Run the unchanged native hosted classifier once on one closed input package."""
    saved=load_json(root/OUTPUT/'admission.json')
    verify_reservation(StateStore(api,ctx).read().state,ctx,plan,row,freeze_sha,saved)
    session=recording.start_run(False,root,id_factory=lambda:row['run_id'],source_issue=row['issue'])
    destination=root/OUTPUT/'attempt'; session.folder.rename(destination);session.folder=destination
    session.record.update(trigger='owner-approved hosted historical evaluation',kind='actual hosted API evaluation',
                          verification_type='hosted model evaluation',campaign_id=plan['campaign_id'],
                          evaluation_slot=row['slot'],github_run_id=ctx.run_id,code_commit=ctx.sha,
                          inference_admitted=True,transport_request_attempts=0,binding=saved,
                          actual_authentication='API key only in trusted hosted gateway')
    try:
        recording.configure(session)
        require(session.record['configuration_sha256']==frozen['configuration_sha256'],'Runtime configuration differs from evaluation freeze')
        if row['kind']=='attack':
            staged=adversarial.prepare(session,row['attack']);prompt=adversarial.prompt(session,staged)
        else:
            staged=staging.prepare(session,packages.load(row['issue'],root));prompt=request.prepare(session,staged)
        require(session.record['input_hashes']==row['input_hashes'],'Staged input differs from frozen case')
        hosted_runtime.record_isolation(session)
        verify_reservation(StateStore(api,ctx).read().state,ctx,plan,row,freeze_sha,saved)
        pipeline.assess(session,staged,prompt,engine_setup=hosted_runtime.prepare_engine,execute=hosted_transport.execute)
    except ClarifierError as error:
        recording.fail(session,error)
    finally:
        transport.close(session);staging.cleanup(session);recording.finish(session)
    return recording.report(session)


def run(root: Path, operation: str, slot: int, freeze_sha: str) -> int:
    """Perform one gated admission or inference; never retry failed model execution."""
    require(operation in ('admit','infer') and type(slot) is int and 1<=slot<=LIMIT,'Invalid evaluation operation/slot')
    ctx=context(json.loads(os.environ['TRUSTED_GITHUB_CONTEXT']))
    plan,frozen=reviewed(root,freeze_sha);row=plan['cases'][slot-1]
    window=int(os.environ['EVALUATION_WINDOW_SECONDS'])
    require(window in (EVALUATION_WINDOW,86400),'Unapproved repository evaluation-window setting')
    plan={**plan,'active_rolling_window_seconds':window}
    token=os.environ.get('GH_TOKEN' if operation=='admit' else 'CLARIFIER_READ_TOKEN')
    require(bool(token),'Job-scoped GitHub token unavailable')
    api=GitHub(token);api.verify_context(ctx)
    (root/OUTPUT).mkdir(parents=True,exist_ok=True)
    if operation=='admit':
        state=transact(StateStore(api,ctx),lambda state:reserve(state,ctx,plan,row,int(time.time())))
        require(state['posting_enabled'] is False,'Posting must remain disabled')
        recording.save_json(root/OUTPUT/'admission.json',binding(ctx,plan,row,freeze_sha))
        return 0
    return infer(root,ctx,api,plan,frozen,row,freeze_sha)


def main() -> int:
    """Return bounded workflow status, retaining failures without public effects."""
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('admit','infer'))
    args=parser.parse_args()
    try:
        slot=int(os.environ['EVALUATION_SLOT']);freeze_sha=os.environ['EVALUATION_FREEZE_SHA256']
        return run(ROOT,args.operation,slot,freeze_sha)
    except (ClarifierError,ValueError,KeyError,OSError) as error:
        output=ROOT/OUTPUT;output.mkdir(parents=True,exist_ok=True)
        if not (output/'failure.json').exists():
            recording.save_json(output/'failure.json',dict(status='blocked',error=recording.redact_text(str(error)),public_actions=[]))
        print(json.dumps(dict(status='blocked',error=recording.redact_text(str(error)),public_actions=[])))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
