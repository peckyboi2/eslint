"""Pure lifetime posting reservations/receipts/reconciliation for task 21."""
from clarifier.controls import ledger
from clarifier.outputs import output_handler as handler
from clarifier.controls import policy as p
from clarifier.outputs.output_handler import CommentPlan
from clarifier.shared.errors import guarded


def reserve(state: dict, plan: CommentPlan, run_id: str) -> dict:
    """Return irrevocable lifetime intent or raise PostingBlocked/StateError."""
    state=ledger.validate(state)
    handler.check_enabled(state)
    if any(row['report']==plan.report for row in state['posts']):
        raise p.PostingBlocked('Lifetime comment intent exists; human reconciliation required')
    row=dict(report=plan.report,input_key=plan.input_key,event_key=plan.event_key,
             marker=plan.marker,run_id=run_id,status='reserved',comment_id=None,configuration=plan.configuration)
    state['posts'].append(row)
    return ledger.validate(state)


def receipt(state: dict, marker: str, comment_id: int | None) -> dict:
    """Record posted ID or uncertain result; never remove/release an intent."""
    state=ledger.validate(state)
    rows=[row for row in state['posts'] if row['marker']==marker]
    if len(rows)!=1 or rows[0]['status']!='reserved': raise p.PostingBlocked('Receipt intent missing or already final')
    if comment_id is not None and (type(comment_id) is not int or comment_id<1): raise p.PostingBlocked('Invalid comment receipt')
    rows[0].update(status='uncertain' if comment_id is None else 'posted',comment_id=comment_id)
    return ledger.validate(state)


@guarded(p.PostingBlocked, 'Malformed reconciliation evidence; lifetime intent remains blocked')
def reconcile(state: dict, marker: str, comments: list[dict], at: int, reason: str) -> dict:
    """Record human-confirmed bot comment; never reopen an absent/ambiguous intent."""
    state=ledger.validate(state)
    rows=[row for row in state['posts'] if row['marker']==marker]
    found=[row for row in comments if f'<!-- {marker} -->' in row.get('body','') and row.get('user',{}).get('login')=='github-actions[bot]' and row.get('user',{}).get('type')=='Bot']
    if len(rows)!=1 or len(found)!=1 or rows[0]['status']=='posted':
        raise p.PostingBlocked('Reconciliation ambiguous; lifetime intent remains blocked')
    rows[0].update(status='posted',comment_id=found[0]['id'])
    state['decisions'].append(dict(actor_id=p.OWNER_ID,at=at,reason=reason,action='reconcile'))
    return ledger.validate(state)
