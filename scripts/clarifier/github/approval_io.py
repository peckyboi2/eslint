"""Trusted exact-output manual approval staging; live release stays absent. Serves C01."""
from pathlib import Path

from clarifier.controls import policy as p
from clarifier.controls import intake_binding
from clarifier.controls.state_store import StateStore
from clarifier.github import workflow_io
from clarifier.inference import recording, staging
from clarifier.outputs import exact_approval, validation
from clarifier.outputs import dynamic_posting, posting
from clarifier.shared import constants as c
from clarifier.shared.errors import guarded


@guarded(p.PostingBlocked, 'Unverified preview artifact')
def load_preview(folder: Path, owner_context, api) -> tuple[dict,str]:
    """Return same-code completed artifact binding/output or raise PostingBlocked."""
    record=validation.parse_json(staging.read_safe(folder,c.RECORD_FILE,c.MAX_INPUT_BYTES).decode())
    binding=record['binding']
    if (record['status']!='completed' or record['public_actions']!=[] or record['tool_calls']!=[]
            or record['transport_request_attempts']!=1 or binding['attempt']!=1
            or binding['sha']!=owner_context.sha or binding['configuration']!=workflow_io.fingerprint()
            or record['source_issue']!=binding['source_issue'] or record['issue_id']!=binding['issue_id']):
        raise p.PostingBlocked('Preview provenance differs from manual approval code')
    run=api._request('GET',f'/repos/{p.REPOSITORY}/actions/runs/{binding["run_id"]}')
    expected=dict(id=int(binding['run_id']),event='issues',run_attempt=1,head_sha=owner_context.sha,
                  path=f'.github/workflows/{p.TRIAGE_WORKFLOW}',status='completed',conclusion='success')
    if any(run.get(key)!=value for key,value in expected.items()):
        raise p.PostingBlocked('Preview run identity/status mismatch')
    inventory=validation.parse_json(staging.read_safe(folder,c.ARTIFACT_HASHES_FILE,c.MAX_INPUT_BYTES).decode())
    for name,digest in inventory.items():
        if recording.sha(staging.read_safe(folder,name,c.MAX_RESPONSE_BYTES)) != digest:
            raise p.PostingBlocked('Preview artifact digest mismatch')
    if not {c.RECORD_FILE,c.RAW_OUTPUT_FILE,c.REQUEST_FILE,c.LOADER_FILE,c.VALIDATION_FILE} <= set(inventory):
        raise p.PostingBlocked('Required native skill/output evidence missing')
    return binding,staging.read_safe(folder,c.RAW_OUTPUT_FILE,c.MAX_OUTPUT_BYTES).decode()


def require_live_release() -> None:
    """Raise PostingBlocked until v10 evaluation and separate posting activation approval."""
    raise p.PostingBlocked('v10 public posting disabled; new frozen evaluations and exact-output owner activation required')


def post_approved(owner_context, api, folder: Path, approval: dict) -> int:
    """Deliver exact approved bytes using existing lifetime intent; caller must gate release."""
    api.verify_context(owner_context)
    binding,raw=load_preview(folder,owner_context,api)
    store=StateStore(api,owner_context)
    edge=dynamic_posting.CommentEdge(api,owner_context,store,binding,approval,raw)
    issue=edge.read_issue()
    ctx=exact_approval.preview_context(binding)
    snapshot=exact_approval.live_snapshot.capture(ctx,issue,issue)
    state=store.read().state
    intake_binding.validate(ctx,snapshot,workflow_io.fingerprint(),binding,state)
    plan=exact_approval.plan(approval,binding,raw,issue,state)
    if plan is None:
        return 0
    comment=posting.deliver(store,edge,plan,binding['run_id'])
    recording.save_json(folder.parent/'posting-receipt.json',dict(comment_id=comment,marker=plan.marker,
                        approval=approval,approving_run=owner_context.run_id))
    return 0
