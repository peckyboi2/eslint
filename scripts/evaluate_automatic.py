#!/usr/bin/env python3
"""Separately approved 13-slot local v10 evaluator; never reuse old quota. Serves D01."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import sys

from clarifier.controls import policy as p
from clarifier.inference import adversarial, packages, pipeline, recording, request, staging, transport
from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError, ConfigurationError, InterruptedRun

ROOT=Path(__file__).resolve().parents[1]
FOLDER=Path('evals/automatic-v10')
PLAN=FOLDER/'evaluation-plan.json'
FREEZE=FOLDER/'evaluation-freeze.json'
APPROVAL=FOLDER/'evaluation-approval.json'
CAMPAIGN=FOLDER/'evaluation'
LIMIT=13
APPROVAL_KEYS={'owner_id','campaign_id','plan_sha256','freeze_sha256','attempt_limit',
               'allow_provider_calls','posting','approved_at','authorization_text'}


def require(value: bool, reason: str) -> None:
    """Raise ConfigurationError on any evaluation/allowance invariant failure."""
    if not value:
        raise ConfigurationError(reason)


def read_pinned(root: Path, name: Path, expected: str) -> dict:
    """Return exact externally hash-bound JSON or raise before provider access."""
    raw=staging.read_safe(root,name.as_posix(),c.MAX_RESPONSE_BYTES)
    require(recording.sha(raw)==expected,'Evaluation plan/freeze hash changed')
    from clarifier.outputs.validation import parse_json
    return parse_json(raw.decode())


def verify_files(root: Path, hashes: dict) -> None:
    """Raise ConfigurationError if any frozen byte differs; no source is copied to models."""
    from verify_automatic import safe_file
    for name,digest in hashes.items():
        path=safe_file(root,name)
        require(path.stat().st_size<=c.MAX_RESPONSE_BYTES,'Frozen file exceeds verification bound')
        raw=path.read_bytes()
        require(recording.sha(raw)==digest,'New evaluation frozen bytes changed: '+name)


def check_plan(plan: dict) -> None:
    """Validate exact fixed case/order/quota policy or raise ConfigurationError."""
    require(plan['new_attempt_limit']==LIMIT and plan['previous_reservations']==54
            and plan['combined_maximum_if_approved']==67,'Unapproved new allowance size')
    require(plan['retries']==0 and plan['refunds']==0 and plan['posting'] is False,'Evaluation must remain no-retry preview')
    rows=plan['cases']
    require(len(rows)==LIMIT and [row['slot'] for row in rows]==list(range(1,LIMIT+1)),'Case slots changed')
    require([row['issue'] for row in rows[:10]]==list(c.HISTORICAL_CASE_IDS),'Historical order changed')
    require([row['attack'] for row in rows[10:]]==list(adversarial.ATTACK_IDS),'Attack order changed')
    expected=('clarify','clarify','human_review',*('no_action',)*7,*('clarify',)*3)
    require(tuple(row['expected_decision'] for row in rows)==expected,'Original expectations changed')
    require(len({row['run_id'] for row in rows})==LIMIT,'Duplicate evaluation run IDs')


def check_approval(approval: dict, plan: dict, plan_sha: str, freeze_sha: str) -> None:
    """Require exact owner allowance record, never report/model-supplied approval."""
    require(set(approval)==APPROVAL_KEYS,'Owner evaluation approval missing/unknown fields')
    expected=dict(owner_id=p.OWNER_ID,campaign_id=plan['campaign_id'],plan_sha256=plan_sha,
                  freeze_sha256=freeze_sha,attempt_limit=LIMIT,allow_provider_calls=True,posting=False)
    require(all(type(approval[key]) is type(value) and approval[key]==value for key,value in expected.items()),
            'Owner approval does not bind this campaign/plan/freeze/allowance')
    require(all(isinstance(approval[key],str) and approval[key].strip()
                for key in ('approved_at','authorization_text')),'Missing direct owner authorization record')


def load_authorised(root: Path, plan_sha: str, freeze_sha: str) -> tuple[dict,dict]:
    """Return frozen authorised plan or raise before reservation/credentials/provider."""
    plan=read_pinned(root,PLAN,plan_sha); check_plan(plan)
    frozen=read_pinned(root,FREEZE,freeze_sha)
    verify_files(root,frozen['files'])
    require(frozen['plan_sha256']==plan_sha,'Freeze binds another evaluation plan')
    from clarifier.outputs.validation import parse_json
    approval=parse_json(staging.read_safe(root,APPROVAL.as_posix(),c.MAX_INPUT_BYTES).decode())
    check_approval(approval,plan,plan_sha,freeze_sha)
    return plan,frozen


def reserve_slot(folder: Path, plan: dict, row: dict, *, at: str) -> dict:
    """Append one ordered reservation exclusively; crashes/failures never refund."""
    check_plan(plan)
    require(row in plan['cases'],'Unknown evaluation slot')
    receipts=folder/'reservations'; receipts.mkdir(parents=True,exist_ok=True)
    with (folder/'admission.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        names={path.name for path in receipts.iterdir()}
        expected={f'{slot:02}.json' for slot in range(1,row['slot'])}
        require(names==expected,'Consumed, skipped, out-of-order or unexpected reservation; no retry')
        receipt=dict(campaign_id=plan['campaign_id'],slot=row['slot'],run_id=row['run_id'],
                     input_hashes=row['input_hashes'],reserved_at=at,owner_id=p.OWNER_ID,
                     attempt_limit=LIMIT,retries=0,refund=False,posting=False)
        recording.save_json(receipts/f'{row["slot"]:02}.json',receipt)
    return receipt


def require_previous_completed(root: Path, plan: dict, slot: int) -> None:
    """Raise before next slot if any prior attempt failed/incomplete; no semantic retry."""
    for row in plan['cases'][:slot-1]:
        path=root/CAMPAIGN/'attempts'/row['run_id']/c.RECORD_FILE
        require(path.is_file(),'Previous reserved attempt has no complete record')
        record=json.loads(path.read_text())
        require(record.get('status')=='completed' and record.get('errors')==[],
                'Previous execution/access failure requires owner review; no automatic continuation')


def prepare_session(root: Path, row: dict, receipt: dict):
    """Return new recorded session or raise; existing attempts cannot be overwritten."""
    session=recording.start_run(False,root,id_factory=lambda:row['run_id'],source_issue=row.get('issue',c.SOURCE_ISSUE))
    destination=root/CAMPAIGN/'attempts'/row['run_id']
    destination.parent.mkdir(parents=True,exist_ok=True)
    require(not destination.exists(),'Evaluation attempt already exists')
    session.folder.rename(destination); session.folder=destination
    recording.mark_local_attempt(session)
    recording.save_json(session.folder/'admission.json',receipt)
    session.record.update(trigger='Darren-approved new v10 local evaluation',campaign_id=receipt['campaign_id'],
                          kind='actual Codex ChatGPT dry run',verification_type='model dry run',inference_admitted=True)
    return session


def prepare_input(session, row: dict):
    """Return staged input/prompt only; expectations never enter the session."""
    if row['kind']=='attack':
        staged=adversarial.prepare(session,row['attack'])
        prompt=adversarial.prompt(session,staged)
    else:
        staged=staging.prepare(session,packages.load(row['issue'],session.root))
        prompt=request.prepare(session,staged)
    require(session.record['input_hashes']==row['input_hashes'],'Actual staged input differs from predeclaration')
    return staged,prompt


def pinned_engine(frozen: dict):
    """Return engine setup edge enforcing local binary hash before local login read."""
    def setup(session):
        found=shutil.which('codex')
        require(bool(found),'Pinned local Codex executable unavailable')
        require(recording.sha(Path(found).resolve().read_bytes())==frozen['engine_binary_sha256'],'Local engine hash changed')
        return transport.prepare_engine(session)
    return setup


def assess(session, row: dict, frozen: dict) -> int:
    """Preserve one attempt and every failure; no comparison labels reach inference."""
    try:
        recording.configure(session)
        require(session.record['configuration_sha256']==frozen['configuration_sha256'],
                'Current inference configuration differs from new freeze')
        staged,prompt=prepare_input(session,row)
        pipeline.assess(session,staged,prompt,engine_setup=pinned_engine(frozen))
        require(session.record['model_returned']==session.config['model'],'Returned model drift; retain failed attempt')
    except ClarifierError as error:
        recording.fail(session,error)
    except KeyboardInterrupt:
        recording.fail(session,InterruptedRun('Evaluation interrupted; reservation consumed'))
    finally:
        transport.close(session)
        staging.cleanup(session)
        recording.finish(session)
    return recording.report(session)


def run_slot(root: Path, slot: int, plan_sha: str, freeze_sha: str) -> int:
    """Run exactly one separately approved slot or raise before unapproved effects."""
    plan,frozen=load_authorised(root,plan_sha,freeze_sha)
    require(type(slot) is int and 1<=slot<=LIMIT,'Invalid evaluation slot')
    require_previous_completed(root,plan,slot)
    row=plan['cases'][slot-1]
    receipt=reserve_slot(root/CAMPAIGN,plan,row,at=recording.utc())
    session=prepare_session(root,row,receipt)
    result=assess(session,row,frozen)
    verify_files(root,frozen['files'])
    return result


def main() -> int:
    """Return CLI status; absent fixed owner approval always blocks model access."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-slot',type=int,required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--freeze-sha256',required=True)
    args=parser.parse_args()
    try:
        return run_slot(ROOT,args.run_slot,args.plan_sha256,args.freeze_sha256)
    except (ClarifierError,ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps(dict(status='blocked',error=recording.redact_text(str(error)),public_actions=[])))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
