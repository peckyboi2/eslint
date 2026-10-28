"""Trusted comment-only privileged orchestrator for tasks 20–21 and 27–28."""
from pathlib import Path
import json

from clarifier.shared import constants as c
from clarifier.shared.errors import guarded
from clarifier.outputs import output_handler as handler
from clarifier.controls import policy as p
from clarifier.outputs import posting_intent as intent
from clarifier.outputs import release_gate
from clarifier.inference.recording import save_json
from clarifier.controls.state_store import StateStore, transact
from clarifier.github import workflow_io as io


class CommentEdge:
    """Fixed comment endpoint only; never reachable by the evaluated model."""
    def __init__(self, api, ctx, store, target):
        """Bind deterministic context, ledger and owner-reviewed sandbox target."""
        self.api,self.ctx,self.store,self.target=api,ctx,store,target

    def read_issue(self) -> dict:
        """Return only the pinned sandbox issue or raise PostingBlocked."""
        if type(self.target.issue) is not int or self.target.issue < 1:
            raise p.PostingBlocked('Approved sandbox target unavailable')
        return self.api._request('GET',f'/repos/{p.REPOSITORY}/issues/{self.target.issue}')

    def create_comment(self, plan: handler.CommentPlan) -> int:
        """Post once after final gates; response loss is uncertain, never retried."""
        self.api.verify_context(self.ctx)
        handler.check_target(self.read_issue(),self.target)
        state=self.store.read().state
        handler.check_enabled(state)
        matches=[r for r in state['posts'] if r['marker']==plan.marker and r['status']=='reserved' and r['report']==plan.report]
        if len(matches)!=1 or plan.report != self.target.issue: raise p.PostingBlocked('Final intent/target mismatch')
        result=self.api._request('POST',f'/repos/{p.REPOSITORY}/issues/{self.target.issue}/comments',{'body':plan.text})
        user=result.get('user',{}) if isinstance(result,dict) else {}
        if (not isinstance(result,dict) or type(result.get('id')) is not int or result['id']<1
                or user.get('login')!='github-actions[bot]' or user.get('type')!='Bot'
                or result.get('body')!=plan.text):
            raise p.PlatformError('Comment response unverified; reconcile before any repost')
        return result['id']


def deliver(store, edge: CommentEdge, plan: handler.CommentPlan, run_id: str) -> int:
    """Reserve, post once and retain receipt; any ambiguous outcome blocks repost."""
    transact(store,lambda state:intent.reserve(state,plan,run_id))
    try:
        comment_id=edge.create_comment(plan)
    except (p.PlatformError,p.PostingBlocked):
        transact(store,lambda state:intent.receipt(state,plan.marker,None))
        raise
    transact(store,lambda state:intent.receipt(state,plan.marker,comment_id))
    return comment_id


@guarded(p.PostingBlocked, 'Cannot validate current-run output artifact; no comment permitted')
def load_output(ctx, binding: dict) -> str:
    """Return one complete same-config adapter result or raise PostingBlocked."""
    folders=[x.parent for x in Path('evals/runs').glob('*/record.json')]
    if len(folders)!=1: raise p.PostingBlocked('Expected one current inference run')
    folder=folders[0]
    record=json.loads((folder/c.RECORD_FILE).read_text())
    if (record.get('status')!='completed' or record.get('source_issue')!=c.SOURCE_ISSUE
            or record.get('model_requested')!=c.FIXED_CONFIG['model']
            or record.get('public_actions')!=[] or record.get('transport_request_attempts')!=1):
        raise p.PostingBlocked('Unverified model run')
    status=json.loads((io.OUTPUT/'inference-status.json').read_text())
    if status != dict(exit_code=0,run_id=ctx.run_id,configuration=io.fingerprint(),verification_type='platform attempt',public_actions=[]):
        raise p.PostingBlocked('Workflow output/configuration mismatch')
    return (folder/c.RAW_OUTPUT_FILE).read_text()


def post_artifact(ctx, api, binding: dict) -> int:
    """Handle exactly one approved live clarification; blocked by absent promotion."""
    handler.check_mode(io.dispatch_mode(),ctx)
    release=release_gate.live_release()
    store=StateStore(api,ctx)
    state=store.read().state
    io.validate_binding(ctx,binding,state)
    edge=CommentEdge(api,ctx,store,p.LIVE_TARGET)
    raw=load_output(ctx,binding)
    plan=handler.plan(raw,ctx,binding['mode'],p.LIVE_TARGET,edge.read_issue(),binding['input_key'],binding['event_key'],binding['configuration']['aggregate_sha256'],state,release)
    if plan is None: return 0
    comment_id=deliver(store,edge,plan,ctx.run_id)
    save_json(io.OUTPUT/'posting-receipt.json',dict(comment_id=comment_id,marker=plan.marker,url=f'https://github.com/{p.REPOSITORY}/issues/{plan.report}#issuecomment-{comment_id}'))
    return 0
