"""Local transactional preview reservations for tasks 25–38; not a GitHub state branch."""
import fcntl
import hashlib
import json
from pathlib import Path
import os
import time

from clarifier.controls import admission
from clarifier.shared import constants as c
from clarifier.controls.identity import Context
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.controls.state_store import Snapshot, transact
from clarifier.inference.staging import read_safe

STATE = Path('evals/checks/gate-c-20261028/dry-state.json')
DEVELOPMENT_DECISION = Path('evals/checks/gate-f-20261028/local-quota-decision.json')


class DryStore:
    """Local compare-parent file store; live branch controls remain unverified."""
    def __init__(self, path: Path):
        """Bind one trusted local state file."""
        self.path=path

    def read(self) -> Snapshot:
        """Return strict local state or raise StateError; never bootstrap implicitly."""
        try: raw=self.path.read_bytes()
        except OSError: raise p.StateError('Local preview ledger missing') from None
        return Snapshot(hashlib.sha256(raw).hexdigest(),ledger.decode(raw))

    def update(self, previous: Snapshot, state: dict) -> None:
        """Atomically replace local state under a short exclusive lock or conflict."""
        data=ledger.encode(state)
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if self.read().parent!=previous.parent: raise p.Conflict('Local state parent changed')
            temporary=self.path.with_suffix('.next')
            with temporary.open('xb') as stream:
                stream.write(data);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)


def initialise(root: Path=c.ROOT) -> None:
    """Create disabled-then-preview owner decision once; no reset/increase API."""
    path=root/STATE
    state=ledger.initial(int(time.time()),'Darren authorised Milestone C dry runs on 2026-10-28')
    state['enabled']=True
    state['decisions'].append(dict(actor_id=p.OWNER_ID,at=int(time.time()),action='enable-preview',reason='Local-only preview campaign; posting disabled; remote Actions remain disabled'))
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream: stream.write(ledger.encode(state))


def reserve(root: Path, run_id: str, source_hashes: dict[str,str]) -> dict:
    """Persist real local count reservation before inference; context is dry-run only."""
    key=admission.input_key(source_hashes)
    context=Context(str(time.time_ns()),1,'0'*40,p.LOCAL_WORKFLOW)
    store=DryStore(root/STATE)
    limit,decision_hash=local_limit(root,store)
    campaign_limit=p.LOCAL_CAMPAIGN_LIMIT if limit==p.LOCAL_DEVELOPMENT_LIMIT else p.CAMPAIGN_LIMIT
    state=transact(store,lambda state:admission.reserve(state,context,key,int(time.time()),rolling_limit=limit,campaign_limit=campaign_limit))
    return dict(verification_type='actual local reservation; GitHub identity/branch simulation only',
                adapter_run_id=run_id,local_context_run_id=context.run_id,input_key=key,rolling_limit=limit,campaign_limit=campaign_limit,quota_decision_sha256=decision_hash,
                event_key=admission.event_key(context,key),campaign=state['campaign'],posting_enabled=state['posting_enabled'])


def read_quota_decision(path: Path, limit: int) -> str:
    """Return an owner-approved local decision hash or raise AdmissionDenied."""
    raw=read_safe(path.parent,path.name,c.MAX_INPUT_BYTES)
    try: decision=json.loads(raw)
    except ValueError: raise p.AdmissionDenied('Malformed local quota decision') from None
    expected={'actor_id':p.OWNER_ID,'scope':p.LOCAL_WORKFLOW,'rolling_limit':limit,'campaign':ledger.CAMPAIGN}
    if limit==p.LOCAL_DEVELOPMENT_LIMIT: expected['campaign_limit']=p.LOCAL_CAMPAIGN_LIMIT
    if not isinstance(decision,dict) or any(decision.get(k)!=v for k,v in expected.items()) or not isinstance(decision.get('authorization_text'),str) or not decision['authorization_text'].strip():
        raise p.AdmissionDenied('Invalid accountable local quota decision')
    return hashlib.sha256(raw).hexdigest()


def record_extension(store, reason: str, at: int) -> None:
    """Append the authorised extension once or raise StateError without resetting state."""
    def record(state):
        if not any(d['action']=='extend-local-preview' and d['reason']==reason for d in state['decisions']):
            state['decisions'].append(dict(actor_id=p.OWNER_ID,at=at,reason=reason,action='extend-local-preview'))
        return state
    transact(store,record)


def local_limit(root: Path, store) -> tuple[int, str | None]:
    """Return the recorded local-only allowance or raise AdmissionDenied/StateError."""
    development=root/DEVELOPMENT_DECISION
    legacy=root/STATE.parent/'local-quota-decision.json'
    if development.exists():
        limit=p.LOCAL_DEVELOPMENT_LIMIT
        decision_hash=read_quota_decision(development,limit)
        reason=p.LOCAL_EXTENSION_REASON+decision_hash
    elif legacy.exists():
        limit=p.LOCAL_EXCEPTION_LIMIT
        decision_hash=read_quota_decision(legacy,limit)
        reason='Owner approved one additional local preview; decision SHA-256 '+decision_hash
    else:
        return p.ROLLING_LIMIT,None
    record_extension(store,reason,int(time.time()))
    return limit,decision_hash
