"""Task 24 integrated infrastructure preflight; no real model/public writes."""
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import Mock

from clarifier.controls import admission
from clarifier.shared.errors import ClarifierError
from clarifier.controls import identity
from clarifier.controls import ledger
from clarifier.outputs import output_handler as handler
from clarifier.controls import policy as p
from clarifier.outputs import posting
from clarifier.outputs.release_gate import Release
from clarifier.tests.test_admission import ctx
from clarifier.tests.test_identity import context_data
from clarifier.tests.test_output_handler import fixture, RAW
from clarifier.tests.test_state_store import MemoryStore


class Preflight(unittest.TestCase):
    def test_full_invalid_output_matrix_never_reaches_public_edge(self):
        result = json.loads(RAW)
        outputs = ['{', RAW + RAW, json.dumps([result]), 'null',
                   RAW.replace('"decision":', '"decision":"clarify","decision":')]
        outputs += [json.dumps({**result, key: value}) for key, value in (
            ('action', 'close'), ('repository', p.REPOSITORY), ('issue', 1), ('force', True))]
        outputs += [json.dumps({**result, 'clarification': text}) for text in (
            'x' * 1501, '@reporter respond', '`@reporter` respond', '<script>bad</script>',
            '[open](https://example.invalid)', '```shell\nrun\n```', 'hidden\u202econtrol', r'escaped\markup')]
        outputs.append(json.dumps({**result, 'rationale': 'x' * 16384}))
        for decision in ('no_action', 'human_review'):
            outputs.append(json.dumps({**result, 'decision': decision}))
        for raw in outputs:
            with self.subTest(raw=raw[:80]):
                model, edge, store = self.pipeline(raw=raw)
                model.assert_called_once()
                edge.create_comment.assert_not_called()
                self.assertEqual(store.state['posts'], [])

    def test_full_target_matrix_never_reserves_or_posts(self):
        changes = [dict(number=None), dict(number=2), dict(repository_url='upstream'),
                   dict(url='https://api.github.com/repos/eslint/eslint/issues/1'),
                   dict(pull_request={}), dict(state='closed'), dict(locked=True),
                   dict(labels=[{'name': 'enhancement'}]), dict(labels=None),
                   dict(body='edited'), dict(body=None), dict(title='edited'), dict(title=None)]
        for change in changes:
            with self.subTest(change=change):
                _, edge, store = self.pipeline(issue_change=change)
                edge.create_comment.assert_not_called()
                self.assertEqual(store.state['posts'], [])

    def test_both_valid_silent_decisions_have_no_intent_or_public_write(self):
        for decision in ('no_action', 'human_review'):
            raw = json.dumps(dict(decision=decision, rationale='Internal only.', clarification=None))
            model, edge, store = self.pipeline(raw=raw)
            model.assert_called_once()
            edge.create_comment.assert_not_called()
            self.assertEqual(store.state['posts'], [])

    def test_changed_source_at_final_edge_blocks_post(self):
        from clarifier.outputs import posting_intent
        from clarifier.tests.test_posting import prepared
        from clarifier.controls.state_store import transact
        for field in ('body', 'title', 'repository_url', 'number', 'labels'):
            store, plan, args = prepared()
            transact(store, lambda state: posting_intent.reserve(state, plan, args['ctx'].run_id))
            api = Mock()
            api._request.return_value = {**args['issue'], field: None}
            edge = posting.CommentEdge(api, args['ctx'], store, args['target'])
            with self.subTest(field=field), self.assertRaises(ClarifierError):
                edge.create_comment(plan)
            self.assertFalse(any(call.args[0] != 'GET' for call in api._request.call_args_list))

    def pipeline(self, data=None, state=None, raw=RAW, issue_change=None, uncertain=False, mode='post'):
        args=fixture();store=MemoryStore();store.state=args['state'] if state is None else state
        model,edge=Mock(return_value=raw),Mock()
        edge.create_comment.side_effect=p.PlatformError('Ambiguous POST') if uncertain else None
        edge.create_comment.return_value=999
        try:
            context=identity.verify(context_data() if data is None else data)
            store.state=admission.reserve(store.state,context,args['source_key'],100)
            output=model()
            config=args['configuration']
            release=Release(config,hashlib.sha256(output.encode()).hexdigest(),'mock-preview',('mock-a','mock-b','mock-c'))
            issue={**args['issue'],**(issue_change or {})}
            plan=handler.plan(output,context,mode,args['target'],issue,args['source_key'],admission.event_key(context,args['source_key']),config,store.state,release)
            if plan: posting.deliver(store,edge,plan,context.run_id)
        except ClarifierError:
            pass
        return model,edge,store

    def test_identity_ref_matrix_zero_model_zero_write(self):
        for key in ('event_name','repository','repository_id','repository_owner_id','actor','actor_id','triggering_actor','ref','workflow_ref','workflow_sha'):
            model,edge,_=self.pipeline(data={**context_data(),key:'wrong'})
            model.assert_not_called();edge.create_comment.assert_not_called()

    def test_disabled_corrupt_exhausted_zero_model_zero_write(self):
        exhausted=fixture()['state']
        for n in range(1,11):exhausted=admission.reserve(exhausted,ctx(n),'a'*64,100)
        for state in (ledger.initial(1,'Mock disabled'),{},exhausted):
            model,edge,_=self.pipeline(state=state)
            model.assert_not_called();edge.create_comment.assert_not_called()

    def test_invalid_and_silent_outputs_zero_write(self):
        outputs=['bad',RAW[:-1]+',"operation":"close"}',json.dumps([json.loads(RAW),json.loads(RAW)])]
        outputs += [json.dumps(dict(decision=d,rationale='Internal only.',clarification=None)) for d in ('no_action','human_review')]
        for raw in outputs:
            model,edge,_=self.pipeline(raw=raw)
            model.assert_called_once();edge.create_comment.assert_not_called()

    def test_wrong_target_pr_nonbug_changed_source_zero_write(self):
        for change in ({'number':2},{'repository_url':'https://api.github.com/repos/eslint/eslint'},{'pull_request':{}},{'body':'changed'},{'labels':[]}):
            model,edge,_=self.pipeline(issue_change=change)
            edge.create_comment.assert_not_called()

    def test_preview_and_rerun_cannot_post(self):
        _,edge,_=self.pipeline(mode='preview');edge.create_comment.assert_not_called()
        _,edge,_=self.pipeline(data={**context_data(),'run_attempt':'2'});edge.create_comment.assert_not_called()

    def test_duplicate_and_uncertain_intent_never_reposts(self):
        _,edge,store=self.pipeline(uncertain=True)
        self.assertEqual(edge.create_comment.call_count,1)
        self.assertEqual(store.state['posts'][0]['status'],'uncertain')
        _,second,_=self.pipeline(state=store.state)
        second.create_comment.assert_not_called()

    def test_known_success_simulates_exactly_one_comment(self):
        model,edge,store=self.pipeline()
        model.assert_called_once();edge.create_comment.assert_called_once()
        self.assertEqual(store.state['posts'][0]['comment_id'],999)
