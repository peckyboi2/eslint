"""Task 22 stop simulations; scheduling/phone/live cancellation are untested."""
import unittest
from unittest.mock import Mock
from clarifier.controls import policy as p
from clarifier import stop
from clarifier.github import stop_io
from clarifier.tests.test_state_store import MemoryStore


class StopTests(unittest.TestCase):
    def test_disables_admission_and_both_run_classes(self):
        store=MemoryStore()
        api=Mock();statuses=[[dict(id=1,status='in_progress'),dict(id=2,status='pending')],
                             [dict(id=1,status='in_progress')],[]]
        def request(method,path,*args):
            if method=='GET' and '/runs?' in path:return {'workflow_runs':statuses.pop(0)}
            return None
        api._request.side_effect=request
        report=stop.execute(api,Mock(),store,100,'Owner stop')
        self.assertFalse(store.state['enabled']);self.assertFalse(store.state['posting_enabled'])
        self.assertEqual(report['unresolved_runs'],[])
        self.assertEqual([r['operation'] for r in report['cancellation_requests']],['cancel','cancel','force-cancel'])
        self.assertFalse(any(p.STOP_WORKFLOW in str(c) for c in api._request.call_args_list))

    def test_corrupt_state_does_not_stop_cancellation(self):
        store=Mock();store.read.side_effect=p.StateError('Corrupt ledger')
        api=Mock();api._request.side_effect=lambda method,path,*args:{'workflow_runs':[]} if method=='GET' else None
        report=stop.execute(api,Mock(),store,100,'Owner stop')
        self.assertTrue(report['workflow_disabled']);self.assertFalse(report['ledger_disabled'])
        self.assertIn('Corrupt ledger',report['errors'])
        self.assertEqual(report['unresolved_runs'],[])

    def test_force_cancel_exhaustion_is_reported(self):
        store=MemoryStore();api=Mock()
        api._request.side_effect=lambda method,path,*args:{'workflow_runs':[dict(id=1,status='in_progress')]} if method=='GET' else None
        report=stop.execute(api,Mock(),store,100,'Owner stop')
        self.assertEqual(report['unresolved_runs'],[1])
        self.assertEqual(len(report['cancellation_requests']),p.STOP_PASSES)

    def test_identity_rejection_reaches_no_write(self):
        api=Mock();api.verify_context.side_effect=p.IdentityError('Rejected')
        with self.assertRaises(p.IdentityError):stop_io.disable_triage(api,Mock(),{})
        api._request.assert_not_called()
