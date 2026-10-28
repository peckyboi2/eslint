"""Task 17 mocked branch conflicts; no live state or public writes."""
import unittest
from unittest.mock import Mock
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.controls.state_store import Snapshot, StateStore, transact


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
