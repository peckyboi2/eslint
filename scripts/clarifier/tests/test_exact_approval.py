"""Synthetic dynamic approval/intent tests; never public posting. Serves C01."""
import json
import unittest
from unittest.mock import Mock

from clarifier.controls import intake_binding, intake_identity, policy as p
from clarifier.inference import live_snapshot
from clarifier.outputs import exact_approval as a, output_handler, posting_intent
from clarifier.outputs import dynamic_posting
from clarifier.github import approval_io
from clarifier.tests.test_intake_identity import fixture
from clarifier.tests.test_intake_admission import enabled
from clarifier.controls import admission


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        data,event=fixture(); self.issue=event['issue']; self.ctx=intake_identity.verify(data,event)
        snap=live_snapshot.capture(self.ctx,self.issue,self.issue)
        self.binding=intake_binding.build(self.ctx,snap,{'aggregate_sha256':'c'*64})
        self.raw=json.dumps(dict(decision='clarify',rationale='Synthetic',clarification='Could you share the missing configuration?'))
        marker=output_handler.attempt_marker(self.ctx,self.binding['event_key'],'c'*64)
        comment=output_handler.format_comment('Could you share the missing configuration?',self.ctx,marker)
        self.approval=a.expected_approval(self.binding,self.raw,comment)
        self.state=admission.reserve(enabled(),self.ctx,self.binding['input_key'],10)
        self.state.update(posting_enabled=True)
        self.state['decisions'].append(dict(actor_id=p.OWNER_ID,at=11,reason='synthetic posting',action='enable-posting'))
        self.provider,self.public=Mock(),Mock()

    def tearDown(self):
        self.provider.assert_not_called(); self.public.assert_not_called()

    def test_exact_dynamic_target_and_lifetime_intent(self):
        plan=a.plan(self.approval,self.binding,self.raw,self.issue,self.state)
        self.assertEqual(plan.report,7)
        state=posting_intent.reserve(self.state,plan,self.ctx.run_id)
        with self.assertRaises(p.PostingBlocked): posting_intent.reserve(state,plan,self.ctx.run_id)
        uncertain=posting_intent.receipt(state,plan.marker,None)
        with self.assertRaises(p.PostingBlocked): posting_intent.reserve(uncertain,plan,self.ctx.run_id)

    def test_every_approval_field_is_exact(self):
        for key in self.approval:
            wrong={**self.approval,key:None}
            with self.subTest(key=key), self.assertRaises(p.PostingBlocked):
                a.plan(wrong,self.binding,self.raw,self.issue,self.state)

    def test_edits_swaps_closure_and_disabled_rejected(self):
        for change in ({'body':'edited'},{'title':'Bug: changed'},{'id':801},{'number':8},{'state':'closed'}):
            with self.subTest(change=change),self.assertRaises(p.PostingBlocked):
                a.plan(self.approval,self.binding,self.raw,{**self.issue,**change},self.state)
        with self.assertRaises(p.PostingBlocked): a.plan(self.approval,self.binding,self.raw,self.issue,enabled())

    def test_silent_outputs_never_create_plan(self):
        for decision in ('no_action','human_review'):
            raw=json.dumps(dict(decision=decision,rationale='Synthetic',clarification=None))
            self.assertIsNone(a.plan({},self.binding,raw,self.issue,self.state))

    def test_live_release_absent(self):
        with self.assertRaises(p.PostingBlocked): approval_io.require_live_release()

    def test_edit_between_approval_and_final_post_recheck(self):
        from clarifier.tests.test_state_store import MemoryStore
        plan=a.plan(self.approval,self.binding,self.raw,self.issue,self.state)
        store=MemoryStore(); store.state=posting_intent.reserve(self.state,plan,self.ctx.run_id)
        api=Mock(); api._request.return_value={**self.issue,'body':'changed after intent'}
        edge=dynamic_posting.CommentEdge(api,Mock(),store,self.binding,self.approval,self.raw)
        with self.assertRaises(p.PostingBlocked): edge.create_comment(plan)
        self.assertEqual([call.args[0] for call in api._request.call_args_list],['GET'])
        self.assertEqual(store.state['posts'][0]['status'],'reserved')
