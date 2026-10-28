"""Task 17 mocked branch conflicts; no live state or public writes."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
from unittest.mock import Mock
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.controls.state_store import Snapshot, StateStore, transact
from clarifier.controls import admission, dry_state
from clarifier.tests.test_admission import enabled, ctx


class RacingStore(dry_state.DryStore):
    """Real atomic-file store with simultaneous first snapshots for task 43."""

    def __init__(self, path):
        super().__init__(path)
        self.barrier = threading.Barrier(2)
        self.local = threading.local()
        self.conflicts = []

    def read(self):
        result = super().read()
        if threading.current_thread() is not threading.main_thread() and not getattr(self.local, 'seen', False):
            self.local.seen = True
            self.barrier.wait(timeout=5)
        return result

    def update(self, previous, state):
        try:
            super().update(previous, state)
        except p.Conflict:
            self.conflicts.append(previous.parent)
            raise


def race(left, right):
    """Return two outcomes after concurrent trusted operations; no network effects."""
    def invoke(operation):
        try:
            operation()
            return 'completed'
        except (p.AdmissionDenied, p.PostingBlocked):
            return 'blocked'
    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(invoke, (left, right)))


class ConcurrentAdmissions(unittest.TestCase):
    def test_races_retain_distinct_quota_and_block_duplicate_original_delivery(self):
        for runs, keys, expected_count in (((1, 2), ('a'*64, 'b'*64), 2),
                                           ((1, 1), ('a'*64, 'a'*64), 1),
                                           ((1, 1), ('a'*64, 'b'*64), 1)):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'state.json'
                path.write_bytes(ledger.encode(enabled()))
                store = RacingStore(path)
                operations = [lambda n=n, key=key: admission.admit(store, ctx(n), key, 100)
                              for n, key in zip(runs, keys)]
                outcomes = race(*operations)
                state = store.read().state
                self.assertEqual(len(state['admissions']), expected_count)
                self.assertEqual(outcomes.count('completed'), expected_count)
                self.assertEqual(state['posts'], [])
                self.assertTrue(store.conflicts)
                self.assertFalse(path.with_suffix('.next').exists())


class MemoryStore:
    def __init__(self):
        self.state=ledger.initial(100,'Setup'); self.parent=0; self.conflict=False
    def read(self): return Snapshot(str(self.parent), ledger.validate(self.state))
    def update(self, previous, state):
        if self.conflict:
            self.conflict=False; self.parent+=1; self.state['decisions'].append(dict(actor_id=p.OWNER_ID, at=101, reason='Competing stop', action='disable'))
            raise p.Conflict('race')
        if previous.parent != str(self.parent): raise p.Conflict('race')
        self.state=ledger.validate(state); self.parent+=1


class StateStoreTests(unittest.TestCase):
    def test_conflict_reapplies_without_lost_record(self):
        store=MemoryStore(); store.conflict=True
        def change(state): state['enabled']=False; return state
        self.assertEqual(len(transact(store, change)['decisions']),2)

    def test_exhaustion_is_bounded(self):
        store=Mock(); store.read.return_value=Snapshot('a',ledger.initial(1,'Setup'))
        store.update.side_effect=p.Conflict('race')
        with self.assertRaises(p.StateError): transact(store, lambda s:s)
        self.assertEqual(store.update.call_count,p.TRANSACTION_ATTEMPTS)

    def test_expected_parent_precedes_git_mutations(self):
        api=Mock(); api._request.return_value={'object':{'sha':'changed'}}
        store=StateStore(api,Mock())
        with self.assertRaises(p.Conflict): store.update(Snapshot('old',ledger.initial(1,'Setup')),ledger.initial(1,'Setup'))
        self.assertEqual([c.args[0] for c in api._request.call_args_list], ['GET'])

    def test_ref_update_is_nonforced_and_parent_bound(self):
        api=Mock(); api._request.side_effect=[{'object':{'sha':'old'}},{'sha':'blob'},{'sha':'tree'},{'sha':'commit'},{}]
        StateStore(api,Mock()).update(Snapshot('old',ledger.initial(1,'Setup')),ledger.initial(1,'Setup'))
        calls=api._request.call_args_list
        self.assertEqual(calls[3].args[2]['parents'],['old'])
        self.assertEqual(calls[4].args[2],{'sha':'commit','force':False})
