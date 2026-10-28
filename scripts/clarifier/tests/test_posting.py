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
