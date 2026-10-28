"""Task 21 posting lifecycle simulations; Mock is not a bot-write test."""
import unittest
from unittest.mock import Mock
from clarifier.controls import admission
from clarifier.outputs import output_handler as h
from clarifier.controls import policy as p
from clarifier.outputs import posting
from clarifier.outputs import posting_intent as intent
from clarifier.controls.state_store import transact
from clarifier.tests.test_output_handler import fixture
from clarifier.tests.test_state_store import MemoryStore


def prepared():
    args=fixture();store=MemoryStore()
    store.state=admission.reserve(args['state'],args['ctx'],args['source_key'],100)
    args['event']=admission.event_key(args['ctx'],args['source_key'])
    args['state']=store.state
    return store,h.plan(**args),args


class PostingTests(unittest.TestCase):
    def test_incomplete_intent_is_corrupt_and_cannot_enable_repost(self):
        from copy import deepcopy
        store, plan, args = prepared()
        transact(store, lambda state: intent.reserve(state, plan, '123'))
        edge = Mock()
        for field in ('marker', 'comment_id', 'event_key', 'configuration', 'status'):
            broken = deepcopy(store.state)
            del broken['posts'][0][field]
            store.state = broken
            with self.subTest(field=field), self.assertRaises(p.StateError):
                posting.deliver(store, edge, plan, '123')
            broken['posts'][0][field] = dict(report=plan.report, input_key=plan.input_key,
                event_key=plan.event_key, marker=plan.marker, run_id='123', status='reserved',
                comment_id=None, configuration=plan.configuration)[field]
        edge.create_comment.assert_not_called()

    def test_incomplete_reconciliation_evidence_fails_with_typed_error_and_no_repost(self):
        from clarifier.shared.errors import ClarifierError
        store, plan, args = prepared()
        transact(store, lambda state: intent.reserve(state, plan, '123'))
        good = dict(id=999, body='<!-- '+plan.marker+' -->', user=dict(login='github-actions[bot]', type='Bot'))
        missing_id = {key: value for key, value in good.items() if key != 'id'}
        variants = [[], [good, good], [missing_id], [{**good, 'id': None}],
                    [{**good, 'body': None}], [{**good, 'user': None}], [None], None,
                    [{**good, 'user': dict(login=p.OWNER, type='User')}]]
        edge = Mock()
        for comments in variants:
            with self.subTest(comments=comments), self.assertRaises(ClarifierError):
                intent.reconcile(store.state, plan.marker, comments, 101, 'Owner review fixture')
            with self.assertRaises(p.PostingBlocked):
                posting.deliver(store, edge, plan, '123')
            self.assertEqual(store.state['posts'][0]['status'], 'reserved')
        edge.create_comment.assert_not_called()

    def test_server_acceptance_lost_response_reconciles_exact_marker_without_repost(self):
        store, plan, args = prepared()
        server_comments = []
        api = Mock()
        def request(method, path, body=None):
            if method == 'GET':
                return args['issue']
            server_comments.append(dict(id=999, body=body['body'], user=dict(login='github-actions[bot]', type='Bot')))
            raise p.PlatformError('Server accepted; response lost')
        api._request.side_effect = request
        edge = posting.CommentEdge(api, args['ctx'], store, args['target'])
        with self.assertRaises(p.PlatformError):
            posting.deliver(store, edge, plan, '123')
        self.assertEqual(store.state['posts'][0]['status'], 'uncertain')
        with self.assertRaises(p.PostingBlocked):
            posting.deliver(store, edge, plan, '123')
        self.assertEqual(len(server_comments), 1)
        transact(store, lambda state: intent.reconcile(state, plan.marker, server_comments, 101,
                                                     'Darren verified complete scan, target URL, bot and exact marker/ID'))
        self.assertEqual(store.state['posts'][0]['comment_id'], 999)
        self.assertEqual(store.state['decisions'][-1]['action'], 'reconcile')
        with self.assertRaises(p.PostingBlocked):
            posting.deliver(store, edge, plan, '123')
        self.assertEqual(len(server_comments), 1)

    def test_concurrent_distinct_inputs_keep_quota_but_only_one_lifetime_comment(self):
        from dataclasses import replace
        from pathlib import Path
        import tempfile
        from clarifier.controls import ledger
        from clarifier.tests.test_admission import ctx
        from clarifier.tests.test_state_store import RacingStore, race
        memory, first, args = prepared()
        second_ctx = ctx(124)
        state = admission.reserve(memory.state, second_ctx, 'c'*64, 100)
        event = admission.event_key(second_ctx, 'c'*64)
        second = replace(first, input_key='c'*64, event_key=event,
                         marker=h.attempt_marker(second_ctx, event, first.configuration))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            path.write_bytes(ledger.encode(state))
            store = RacingStore(path)
            edge = Mock()
            edge.create_comment.return_value = 999
            outcomes = race(lambda: posting.deliver(store, edge, first, '123'),
                            lambda: posting.deliver(store, edge, second, '124'))
            self.assertEqual(sorted(outcomes), ['blocked', 'completed'])
            self.assertEqual(len(store.read().state['admissions']), 2)
            self.assertEqual(len(store.read().state['posts']), 1)
            edge.create_comment.assert_called_once()
            self.assertTrue(store.conflicts)

    def test_stop_winning_state_conflict_blocks_posting_reservation(self):
        from clarifier.github import stop_io
        store, plan, args = prepared()
        original = store.update
        stopped = False
        def update(previous, state):
            nonlocal stopped
            if not stopped:
                stopped = True
                store.state = stop_io.disabled(store.state, 101, 'Stop wins reservation race')
                store.parent += 1
                raise p.Conflict('Stop changed expected parent')
            original(previous, state)
        store.update = update
        edge = Mock()
        with self.assertRaises(p.PostingBlocked):
            posting.deliver(store, edge, plan, '123')
        edge.create_comment.assert_not_called()
        self.assertEqual(store.state['posts'], [])
        self.assertEqual(len(store.state['admissions']), 1)

    def test_stop_after_final_check_records_unavoidable_inflight_write(self):
        from clarifier.github import stop_io
        store, plan, args = prepared()
        api = Mock()
        def request(method, path, body=None):
            if method == 'GET':
                return args['issue']
            self.assertEqual(method, 'POST')
            self.assertTrue(path.endswith('/issues/1/comments'))
            store.state = stop_io.disabled(store.state, 101, 'Stop after final check')
            store.parent += 1
            return dict(id=999, body=plan.text, user=dict(login='github-actions[bot]', type='Bot'))
        api._request.side_effect = request
        edge = posting.CommentEdge(api, args['ctx'], store, args['target'])
        self.assertEqual(posting.deliver(store, edge, plan, '123'), 999)
        self.assertFalse(store.state['enabled'])
        self.assertEqual(store.state['posts'][0]['status'], 'posted')
        self.assertEqual(sum(call.args[0] == 'POST' for call in api._request.call_args_list), 1)
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(store.state, args['ctx'], plan.input_key, 102)

    def test_intent_precedes_single_post_and_receipt(self):
        store,plan,args=prepared();edge=Mock()
        def create(_):
            self.assertEqual(store.state['posts'][0]['status'],'reserved'); return 999
        edge.create_comment.side_effect=create
        self.assertEqual(posting.deliver(store,edge,plan,'123'),999)
        self.assertEqual(store.state['posts'][0]['comment_id'],999)
        with self.assertRaises(p.PostingBlocked):posting.deliver(store,edge,plan,'123')
        self.assertEqual(edge.create_comment.call_count,1)

    def test_response_loss_leaves_uncertain_without_retry(self):
        store,plan,args=prepared();edge=Mock()
        edge.create_comment.side_effect=p.PlatformError('Lost response after server acceptance')
        with self.assertRaises(p.PlatformError):posting.deliver(store,edge,plan,'123')
        self.assertEqual(store.state['posts'][0]['status'],'uncertain')
        with self.assertRaises(p.PostingBlocked):posting.deliver(store,edge,plan,'123')
        self.assertEqual(edge.create_comment.call_count,1)

    def test_receipt_write_loss_retains_reserved_lifetime_block(self):
        store,plan,args=prepared();edge=Mock();edge.create_comment.return_value=999
        original=store.update
        def update(previous,state):
            if state['posts'] and state['posts'][0]['status']=='posted':raise p.PlatformError('Receipt write lost')
            original(previous,state)
        store.update=update
        with self.assertRaises(p.PlatformError):posting.deliver(store,edge,plan,'123')
        self.assertEqual(store.state['posts'][0]['status'],'reserved')
        with self.assertRaises(p.PostingBlocked):posting.deliver(store,edge,plan,'123')
        edge.create_comment.assert_called_once()

    def test_human_reconciliation_never_clears_intent(self):
        store,plan,args=prepared()
        transact(store,lambda state:intent.reserve(state,plan,'123'))
        with self.assertRaises(p.PostingBlocked):intent.reconcile(store.state,plan.marker,[],101,'Owner inspection')
        found=[dict(id=999,body='<!-- '+plan.marker+' -->',user=dict(login='github-actions[bot]',type='Bot'))]
        state=intent.reconcile(store.state,plan.marker,found,101,'Owner confirmed marker and comment URL')
        self.assertEqual(state['posts'][0]['status'],'posted')
        self.assertEqual(state['decisions'][-1]['actor_id'],p.OWNER_ID)

    def test_final_enabled_source_and_identity_checks_precede_post(self):
        store,plan,args=prepared();api=Mock()
        transact(store,lambda state:intent.reserve(state,plan,'123'))
        api._request.return_value=args['issue']
        store.state['enabled']=False;store.state['posting_enabled']=False
        store.state['decisions'].append(dict(actor_id=p.OWNER_ID,at=101,reason='Mock stop',action='disable'))
        edge=posting.CommentEdge(api,args['ctx'],store,args['target'])
        with self.assertRaises(p.PostingBlocked):edge.create_comment(plan)
        self.assertEqual([call.args[0] for call in api._request.call_args_list],['GET'])
