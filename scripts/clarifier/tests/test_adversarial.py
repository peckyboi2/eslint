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

    def test_local_reservations_persist_without_enabling_posting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dry_state.initialise(root)
            first=dry_state.reserve(root,'adapter-a',c.APPROVED)
            second=dry_state.reserve(root,'adapter-b',c.APPROVED)
            state=dry_state.DryStore(root/dry_state.STATE).read().state
            self.assertEqual(len(state['admissions']),2)
            self.assertFalse(state['posting_enabled'])
            self.assertNotEqual(first['event_key'],second['event_key'])
