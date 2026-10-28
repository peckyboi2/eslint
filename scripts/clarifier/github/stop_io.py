"""Independent bounded stop effects and inspection for task 22."""
from clarifier.shared.errors import ClarifierError, guarded
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.controls.state_store import StateStore, transact

RUN_PAGES = 10


def disabled(state: dict, at: int, reason: str) -> dict:
    """Return accountable disabled state; retain all quota/posting reservations."""
    state=ledger.validate(state)
    state.update(enabled=False,posting_enabled=False)
    state['decisions'].append(dict(actor_id=p.OWNER_ID,at=at,reason=reason,action='disable'))
    return ledger.validate(state)


def disable_admission(store, at: int, reason: str, report: dict) -> None:
    """Try bounded ledger disable; preserve errors so cancellation still runs."""
    try:
        state=transact(store,lambda state:disabled(state,at,reason))
        report['ledger_disabled']=True
        report['inflight_intents']=[r for r in state['posts'] if r['status']!='posted']
    except ClarifierError as error:
        report['errors'].append(str(error))
        report['ledger_disabled']=False


def disable_triage(api, ctx, report: dict) -> None:
    """Disable only triage, independently of ledger corruption or triage locks."""
    api.verify_context(ctx)
    path=f'/repos/{p.REPOSITORY}/actions/workflows/{p.TRIAGE_WORKFLOW}/disable'
    try:
        api._request('PUT',path)
        report['workflow_disabled']=True
    except ClarifierError as error:
        report['errors'].append(str(error));report['workflow_disabled']=False


@guarded(p.PlatformError, "Run inspection response malformed")
def active_runs(api) -> list[dict]:
    """Return noncompleted triage runs or fail closed if the bounded scan is full."""
    result=[]
    for page in range(1,RUN_PAGES+1):
        data=api._request('GET',f'/repos/{p.REPOSITORY}/actions/workflows/{p.TRIAGE_WORKFLOW}/runs?per_page=100&page={page}')
        rows=data['workflow_runs']
        result.extend(row for row in rows if row['status']!='completed')
        if len(rows)<100: return result
    raise p.PlatformError('Run inspection bound reached; manual Actions inspection required')


def cancel_runs(api, ctx, report: dict) -> None:
    """Cancel then force-cancel unresolved runs in bounded passes, with verification."""
    for attempt in range(p.STOP_PASSES):
        api.verify_context(ctx)
        try: rows=active_runs(api)
        except ClarifierError as error:
            report['errors'].append(str(error));return
        if not rows: report['unresolved_runs']=[];return
        report['unresolved_runs']=[row['id'] for row in rows]
        for row in rows:
            operation='cancel' if attempt==0 else 'force-cancel'
            try:
                api._request('POST',f'/repos/{p.REPOSITORY}/actions/runs/{int(row["id"])}/{operation}')
                report['cancellation_requests'].append(dict(run_id=row['id'],operation=operation))
            except ClarifierError as error: report['errors'].append(str(error))
    try: report['unresolved_runs']=[row['id'] for row in active_runs(api)]
    except ClarifierError as error: report['errors'].append(str(error))


def inspect_writes(api, ctx, store, report: dict) -> None:
    """Preserve in-flight intents/visible markers; never undo or repost a write."""
    try:
        state=store.read().state
        rows=[r for r in state['posts'] if r['status']!='posted']
        report['inflight_intents']=rows
        report['visible_inflight_comments']=[]
        for row in rows:
            comments=api._request('GET',f'/repos/{p.REPOSITORY}/issues/{row["report"]}/comments?per_page=100')
            found=[c['id'] for c in comments if f'<!-- {row["marker"]} -->' in c.get('body','')]
            report['visible_inflight_comments'].append(dict(marker=row['marker'],comment_ids=found))
            if len(comments)>=100: report['errors'].append('Comment inspection truncated; inspect manually')
    except ClarifierError as error: report['errors'].append(str(error))
