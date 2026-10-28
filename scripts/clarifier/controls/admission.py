"""Pure irrevocable inference reservations and limits for task 18."""
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
    return hashlib.sha256(f'{p.REPOSITORY_ID}:{context.run_id}:{source_key}'.encode()).hexdigest()


def reserve(state: dict, context: Context, source_key: str, at: int, *, rolling_limit: int = p.ROLLING_LIMIT) -> dict:
    """Return appended admission or raise AdmissionDenied/StateError; never refund."""
    state = ledger.validate(state)
    key = event_key(context, source_key)
    if not state['enabled']: raise p.AdmissionDenied('Admission disabled')
    if not ledger.integer(at) or not ledger.digest(source_key): raise p.AdmissionDenied('Invalid reservation input')
    if any(a['at'] > at for a in state['admissions']): raise p.AdmissionDenied('Ledger clock is ahead; human review required')
    if any(a['event_key'] == key or a['run_id'] == context.run_id for a in state['admissions']):
        raise p.AdmissionDenied('Original run/event already admitted; no automatic retry')
    if rolling_limit != p.ROLLING_LIMIT and not (rolling_limit == p.LOCAL_EXCEPTION_LIMIT and context.workflow == p.LOCAL_WORKFLOW and any(d['action']=='extend-local-preview' for d in state['decisions'])):
        raise p.AdmissionDenied('Unapproved limit increase')
    recent = sum(a['at'] > at-p.ROLLING_SECONDS for a in state['admissions'])
    if recent >= rolling_limit: raise p.AdmissionDenied('Rolling quota exhausted')
    if len(state['admissions']) >= p.CAMPAIGN_LIMIT: raise p.AdmissionDenied('Campaign quota exhausted')
    state['admissions'].append(dict(run_id=context.run_id, event_key=key, input_key=source_key, at=at, campaign=state['campaign']))
    return ledger.validate(state)


def admit(store, context: Context, source_key: str, at: int) -> dict:
    """Persist quota before inference or raise a terminal admission denial."""
    return transact(store, lambda state: reserve(state, context, source_key, at))
