"""Task 28 replay infrastructure tests; no live posting or model invocation."""
from dataclasses import replace
import unittest
from unittest.mock import Mock

from clarifier.controls import admission
from clarifier.controls import identity
from clarifier.controls import ledger
from clarifier.outputs import output_handler as h
from clarifier.controls import policy as p
from clarifier.outputs import posting
from clarifier.tests.test_identity import context_data
from clarifier.tests.test_posting import prepared


class ReplayTests(unittest.TestCase):
    def test_same_original_event_and_rerun_block_before_model_or_write(self):
        store,plan,args=prepared();edge=Mock();edge.create_comment.return_value=999
        posting.deliver(store,edge,plan,'123')
        for attempt in ('1','2'):
            ctx=identity.verify({**context_data(),'run_attempt':attempt})
            model=Mock()
            with self.assertRaises(p.AdmissionDenied):
                admission.reserve(store.state,ctx,plan.input_key,101);model()
            model.assert_not_called()
        self.assertEqual(edge.create_comment.call_count,1)

    def test_new_event_and_changed_input_cannot_bypass_lifetime_limit(self):
        store,plan,args=prepared();edge=Mock();edge.create_comment.return_value=999
        posting.deliver(store,edge,plan,'123')
        for number,key in (('124',plan.input_key),('125','c'*64)):
            ctx=identity.verify({**context_data(),'run_id':number})
            state=admission.reserve(store.state,ctx,key,101);store.state=state
            event=admission.event_key(ctx,key)
            self.assertNotEqual(event,plan.event_key)
            replay=replace(plan,input_key=key,event_key=event,marker=h.attempt_marker(ctx,event,plan.configuration))
            with self.assertRaises(p.PostingBlocked):posting.deliver(store,edge,replay,number)
        self.assertEqual(edge.create_comment.call_count,1)
        self.assertEqual(len(store.state['posts']),1)
        self.assertEqual(store.state['posts'][0]['comment_id'],999)

    def test_posted_receipt_cannot_be_rewritten_or_removed(self):
        store,plan,args=prepared();edge=Mock();edge.create_comment.return_value=999
        posting.deliver(store,edge,plan,'123')
        previous=ledger.validate(store.state)
        changed=ledger.validate(previous);changed['posts'][0]['comment_id']=1000
        with self.assertRaises(p.StateError):ledger.validate_transition(previous,changed)
        changed=ledger.validate(previous);changed['posts']=[]
        with self.assertRaises(p.StateError):ledger.validate_transition(previous,changed)
        self.assertEqual(edge.create_comment.call_count,1)
