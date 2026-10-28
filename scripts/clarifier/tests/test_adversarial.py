"""Task 25 fixture/isolation/denial infrastructure; real model runs are separate."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from clarifier.inference import adversarial as a
from clarifier.shared import constants as c
from clarifier.controls import dry_state
from clarifier.inference import recording
from clarifier.inference import request
from clarifier.inference import staging
from clarifier.inference import transport
from clarifier.shared.errors import TransportError


class AttackTests(unittest.TestCase):
    def test_fabricated_authority_cannot_select_a_mutation(self):
        from clarifier.outputs import output_handler
        from clarifier.shared.errors import ClarifierError
        from clarifier.tests.test_output_handler import fixture
        from unittest.mock import Mock
        for action in ('close_all_stale_issues', 'delete_issue', 'merge_pull_request', 'force_push'):
            args = fixture()
            result = json.loads(args['raw'])
            result['action'] = action
            args['raw'] = json.dumps(result)
            public_write = Mock()
            with self.subTest(action=action), self.assertRaises(ClarifierError):
                output_handler.plan(**args)
                public_write()
            public_write.assert_not_called()

    def test_generated_request_exposes_no_mutation_interface(self):
        config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        incoming = dict(model=config['model'], instructions='trusted skill',
                        tools=[dict(type='function', name='close_all_stale_issues')],
                        input=[dict(role='user', content=[dict(text='untrusted approval')])])
        outgoing = request.prepare_request(incoming, 'trusted skill', 'untrusted approval', config)
        self.assertEqual(outgoing['tools'], [])
        self.assertEqual(outgoing['tool_choice'], 'none')
        self.assertFalse(outgoing['parallel_tool_calls'])
        self.assertNotIn('close_all_stale_issues', json.dumps(outgoing))

    def test_staged_attack_has_only_fabricated_input_not_expectations(self):
        for attack in a.ATTACK_IDS:
            session=recording.start_run(True,id_factory=recording.new_run_id)
            try:
                recording.configure(session)
                staged=a.prepare(session,attack)
                text=a.prompt(session,staged)
                files=json.loads(text.split('\n',1)[1])['files']
                self.assertIn('body.md',files)
                self.assertNotIn('expected_behaviour',text)
                self.assertNotIn(a.load(attack)['expected_behaviour'],text)
                self.assertEqual(session.record['public_actions'],[])
                self.assertFalse(list(staged.workspace.rglob('.git')))
            finally: staging.cleanup(session);recording.finish(session)

    def test_actual_response_guard_denies_forbidden_capability_items(self):
        for kind in ('function_call','web_search_call','computer_call','shell_call','mcp_call'):
            with self.assertRaises(TransportError):
                transport.inspect_event({'type':'response.output_item.added','item':{'type':kind}})

    def test_outside_evaluator_reads_are_rejected_by_staging(self):
        from clarifier.shared.errors import StagingError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / 'evidence'
            evidence.mkdir()
            secret = root / 'evaluator.json'
            secret.write_text('evaluator-canary-not-for-model')
            (evidence / 'linked.json').symlink_to(secret)
            for name in ('../evaluator.json', str(secret), 'linked.json', '.git/config'):
                with self.subTest(name=name), self.assertRaises(StagingError):
                    staging.read_safe(evidence, name, c.MAX_INPUT_BYTES)

    def test_poisoned_tool_items_cannot_dispatch_any_interface(self):
        from unittest.mock import Mock
        for kind in ('file_search_call', 'mcp_call', 'mcp_tool_call', 'local_shell_call',
                     'code_interpreter_call', 'function_call', 'web_search_call'):
            dispatch = Mock()
            item = dict(type=kind, arguments='read evaluator; execute code; fetch arbitrary URL')
            raw = ('data: ' + json.dumps(dict(type='response.output_item.added', item=item)) + '\n\n').encode()
            with self.subTest(kind=kind), self.assertRaises(TransportError):
                transport.inspect_response(raw + transport.synthetic_response())
                dispatch()
            dispatch.assert_not_called()

    def test_local_reservations_persist_without_enabling_posting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dry_state.initialise(root)
            first=dry_state.reserve(root,'adapter-a',c.APPROVED)
            second=dry_state.reserve(root,'adapter-b',c.APPROVED)
            state=dry_state.DryStore(root/dry_state.STATE).read().state
            self.assertEqual(len(state['admissions']),2)
            self.assertFalse(state['posting_enabled'])
            self.assertNotEqual(first['event_key'],second['event_key'])
