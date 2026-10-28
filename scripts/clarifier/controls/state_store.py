"""Expected-parent, non-forced state-branch transactions for task 17."""
import base64
from collections.abc import Callable
from dataclasses import dataclass

from clarifier.shared.errors import guarded
from clarifier.controls import ledger
from clarifier.controls import policy as p


@dataclass(frozen=True)
class Snapshot:
    """One immutable branch parent and its validated state."""
    parent: str
    state: dict


class StateStore:
    """Deterministic state edge, bound to verified caller context."""
    def __init__(self, api, context):
        """Construct a store without reading credentials or mutating state."""
        self.api, self.context = api, context
        self._root = f'/repos/{p.REPOSITORY}/git/'

    @guarded(p.StateError, "State branch missing or malformed")
    def read(self) -> Snapshot:
        """Return the validated dedicated branch snapshot or fail closed."""
        self.api.verify_context(self.context)
        parent = self.api._request('GET', self._root+'ref/'+p.STATE_REF)['object']['sha']
        commit = self.api._request('GET', self._root+'commits/'+parent)
        tree = self.api._request('GET', self._root+'trees/'+commit['tree']['sha'])
        rows = tree.get('tree', [])
        ledger.check(not tree.get('truncated') and len(rows) == 1, 'Unexpected state branch tree')
        row = rows[0]
        ledger.check(row.get('path') == p.STATE_FILE and row.get('type') == 'blob' and row.get('mode') == '100644', 'Invalid state blob')
        blob = self.api._request('GET', self._root+'blobs/'+row['sha'])
        ledger.check(blob.get('encoding') == 'base64', 'Unknown blob encoding')
        return Snapshot(parent, ledger.decode(base64.b64decode(blob['content'])))

    @guarded(p.StateError, "State transaction failed; inspect ledger before retry")
    def update(self, previous: Snapshot, state: dict) -> None:
        """Commit against expected parent; raise Conflict rather than lose a reservation."""
        ledger.validate_transition(previous.state, state)
        encoded = ledger.encode(state)
        self.api.verify_context(self.context)
        head = self.api._request('GET', self._root+'ref/'+p.STATE_REF)['object']['sha']
        if head != previous.parent: raise p.Conflict('Expected state parent changed')
        blob = self.api._request('POST', self._root+'blobs', {'content': base64.b64encode(encoded).decode(), 'encoding': 'base64'})
        tree = self.api._request('POST', self._root+'trees', {'tree': [{'path': p.STATE_FILE, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}]})
        commit = self.api._request('POST', self._root+'commits', {'message': 'clarifier: transactional state update', 'tree': tree['sha'], 'parents': [previous.parent]})
        self.api.verify_context(self.context)
        self.api._request('PATCH', self._root+'refs/'+p.STATE_REF, {'sha': commit['sha'], 'force': False})


def transact(store, change: Callable[[dict], dict]) -> dict:
    """Reapply a pure change on fresh state after bounded conflicts; never refund."""
    for _ in range(p.TRANSACTION_ATTEMPTS):
        previous = store.read()
        updated = ledger.validate(change(ledger.validate(previous.state)))
        ledger.validate_transition(previous.state, updated)
        try:
            store.update(previous, updated)
            return updated
        except p.Conflict:
            continue
    raise p.StateError('State conflicts exhausted; no automatic delayed retry')
