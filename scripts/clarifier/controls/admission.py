"""Pure irrevocable inference reservations and limits for tasks 18, 29."""
import hashlib
import json

from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.controls.identity import Context
from clarifier.controls.state_store import transact


def input_key(hashes: dict[str, str]) -> str:
    """Return the approved source identity or raise AdmissionDenied."""
    if not hashes or not all(isinstance(k,str) and ledger.digest(v) for k,v in hashes.items()):
        raise p.AdmissionDenied('Invalid input hashes')
    return hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def event_key(context: Context, source_key: str) -> str:
    """Return stable original-run dedup key; rerun attempts keep this identity."""
    if context.event_name == 'issues':
        if type(context.issue_id) is not int or context.issue_id <= 0 or context.attempt != 1:
            raise p.AdmissionDenied('Invalid issue-event identity')
        return hashlib.sha256(f'{p.REPOSITORY_ID}:issue:{context.issue_id}:opened'.encode()).hexdigest()
    return hashlib.sha256(f'{p.REPOSITORY_ID}:{context.run_id}:{source_key}'.encode()).hexdigest()


def local_extension_allowed(state: dict, context: Context, limit: int) -> bool:
    """Return whether an accountable decision permits this local-only limit."""
    if context.workflow != p.LOCAL_WORKFLOW:
        return False
    extensions = [row for row in state['decisions'] if row['action'] == 'extend-local-preview']
    if limit == p.LOCAL_EXCEPTION_LIMIT:
        return bool(extensions)
    if limit != p.LOCAL_DEVELOPMENT_LIMIT:
        return False
    return any(row['reason'].startswith(p.LOCAL_EXTENSION_REASON)
               and ledger.digest(row['reason'][len(p.LOCAL_EXTENSION_REASON):]) for row in extensions)


def reserve(state: dict, context: Context, source_key: str, at: int, *, rolling_limit: int = p.ROLLING_LIMIT,
            campaign_limit: int = p.CAMPAIGN_LIMIT) -> dict:
    """Return appended admission or raise AdmissionDenied/StateError; never refund."""
    state = ledger.validate(state)
    key = event_key(context, source_key)
    if not state['enabled']: raise p.AdmissionDenied('Admission disabled')
    if not ledger.integer(at) or not ledger.digest(source_key): raise p.AdmissionDenied('Invalid reservation input')
    if any(a['at'] > at for a in state['admissions']): raise p.AdmissionDenied('Ledger clock is ahead; human review required')
    if any(a['event_key'] == key or a['run_id'] == context.run_id for a in state['admissions']):
        raise p.AdmissionDenied('Original run/event already admitted; no automatic retry')
    if rolling_limit != p.ROLLING_LIMIT and not local_extension_allowed(state, context, rolling_limit):
        raise p.AdmissionDenied('Unapproved limit increase')
    if campaign_limit != p.CAMPAIGN_LIMIT and not (campaign_limit == p.LOCAL_CAMPAIGN_LIMIT
            and context.workflow == p.LOCAL_WORKFLOW and ledger.local_campaign_limit(state) == campaign_limit):
        raise p.AdmissionDenied('Unapproved campaign limit increase')
    recent = sum(a['at'] > at-p.ROLLING_SECONDS for a in state['admissions'])
    if recent >= rolling_limit: raise p.AdmissionDenied('Rolling quota exhausted')
    if len(state['admissions']) >= campaign_limit: raise p.AdmissionDenied('Campaign quota exhausted')
    state['admissions'].append(dict(run_id=context.run_id, event_key=key, input_key=source_key, at=at, campaign=state['campaign']))
    return ledger.validate(state)


def admit(store, context: Context, source_key: str, at: int) -> dict:
    """Persist quota before inference or raise a terminal admission denial."""
    return transact(store, lambda state: reserve(state, context, source_key, at))
