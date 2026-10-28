"""Task 22 stop simulations; scheduling/phone/live cancellation are untested."""
import unittest
from unittest.mock import Mock
from clarifier.controls import policy as p
from clarifier import stop
from clarifier.github import stop_io
from clarifier.tests.test_state_store import MemoryStore


class StopTests(unittest.TestCase):
    def test_busy_stop_keeps_inflight_marker_and_blocks_future_admission(self):
        from clarifier.controls import admission, identity
        from clarifier.outputs import posting_intent
        from clarifier.controls.state_store import transact
        from clarifier.tests.test_posting import prepared
        from clarifier.tests.test_identity import context_data
        from clarifier.tests.test_admission import ctx
        store, plan, args = prepared()
        transact(store, lambda state: posting_intent.reserve(state, plan, '123'))
        context = identity.verify(context_data(p.STOP_WORKFLOW), p.STOP_WORKFLOW)
        statuses = [[dict(id=1, status='in_progress'), dict(id=2, status='pending')],
                    [dict(id=1, status='in_progress')], []]
        api = Mock()
        def request(method, path, body=None):
            if method == 'GET' and '/runs?' in path:
                return dict(workflow_runs=statuses.pop(0))
            if method == 'GET' and '/comments?' in path:
                return [dict(id=999, body='<!-- '+plan.marker+' -->')]
            self.assertTrue(p.TRIAGE_WORKFLOW in path or '/actions/runs/' in path)
            return None
        api._request.side_effect = request
        report = stop.execute(api, context, store, 101, 'Phone sequence simulation')
        self.assertTrue(report['ledger_disabled'])
        self.assertTrue(report['workflow_disabled'])
        self.assertEqual(report['unresolved_runs'], [])
        self.assertEqual({row['run_id'] for row in report['cancellation_requests']}, {1, 2})
        self.assertEqual(report['visible_inflight_comments'], [dict(marker=plan.marker, comment_ids=[999])])
        self.assertEqual(store.state['posts'][0]['status'], 'reserved')
        model, public_write = Mock(), Mock()
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(store.state, ctx(999), 'a'*64, 102)
            model()
            public_write()
        model.assert_not_called()
        public_write.assert_not_called()
        self.assertEqual(report['public_actions'], [])

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
