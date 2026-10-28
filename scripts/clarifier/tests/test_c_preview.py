"""Task 29 fresh-case and quota-boundary simulations; never actual inference."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from clarifier import c_preview
from clarifier.controls import dry_state, policy
from clarifier.shared import constants as c
from clarifier.inference import packages, recording
from clarifier.tests.test_preview import RunFixture


class CasePreview(RunFixture):
    def setUp(self):
        super().setUp()
        shutil.copytree(c.ROOT / c.PREPARED_PATH, self.root / c.PREPARED_PATH, dirs_exist_ok=True)
        dry_state.initialise(self.root)

    def run_case(self, issue, attack=None):
        output = io.StringIO()
        with redirect_stdout(output):
            code = c_preview.run(attack, case_id=issue, root=self.root)
        folder = Path(json.loads(output.getvalue())['folder'])
        return code, folder, json.loads((folder / 'record.json').read_text())

    def test_synthetic_case_run_has_complete_support_fresh_request_and_no_writes(self):
        for issue, decision in ((19847, 'no_action'), (19924, 'human_review'), (20606, 'clarify')):
            with self.subTest(issue=issue):
                self.raw = json.dumps({'decision': decision, 'rationale': 'Synthetic lifecycle only.',
                                      'clarification': 'Could you share the missing setup?' if decision == 'clarify' else None})
                code, folder, record = self.run_case(issue)
                self.assertEqual(code, 0)
                self.assertEqual(record['source_issue'], issue)
                self.assertTrue(record['inference_admitted'])
                prompt = json.loads((folder / 'prompt.txt').read_text().split('\n', 1)[1])
                self.assertEqual(set(prompt['files']), set(packages.load(issue).hashes))
                route = json.loads((folder / 'validation.json').read_text())
                self.assertEqual(route['source_issue'],issue)
                self.assertEqual(route['public_actions'], [])
                if decision != 'clarify':
                    self.assertIsNone(route['preview_comment'])
                self.assertEqual(record['public_actions'], [])
                self.assertFalse(record['posting_available'])
                self.assertFalse(Path(record['model_workspace']).exists())
        state = dry_state.DryStore(self.root / dry_state.STATE).read().state
        self.assertEqual(len(state['admissions']), 3)
        self.assertFalse(state['posting_enabled'])
        self.network.assert_not_called()

    def test_exhausted_quota_stops_before_skill_credentials_engine_or_public_write(self):
        with patch.object(dry_state.time, 'time_ns', side_effect=range(1, 12)):
            for index in range(policy.ROLLING_LIMIT):
                dry_state.reserve(self.root, f'fixture-{index}', c.APPROVED)
            before = (self.root / dry_state.STATE).read_bytes()
            code, folder, record = self.run_case(19118)
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.assertEqual(record['errors'], ['Rolling quota exhausted'])
        self.assertEqual(record['transport_request_attempts'], 0)
        self.assertFalse(record['inference_admitted'])
        self.assertEqual(record['public_actions'], [])
        self.assertFalse(record['posting_available'])
        self.assertTrue((folder / 'prompt.txt').is_file())
        self.assertEqual(before, (self.root / dry_state.STATE).read_bytes())
        for name in ('invocation.json', 'request.json', 'loader.json', 'admission.json'):
            self.assertFalse((folder / name).exists())
        self.version.assert_not_called()
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()
        self.network.assert_not_called()

    def test_unapproved_case_and_mixed_attack_are_silent_without_reservation(self):
        for issue, attack in ((99999, None), (20606, 'fabricated-approval')):
            code, folder, record = self.run_case(issue, attack)
            self.assertEqual((code, record['status']), (1, 'failed'))
            self.assertEqual(record['public_actions'], [])
            self.assertFalse(record['posting_available'])
            self.assertFalse((folder / 'admission.json').exists())
        self.assertEqual(dry_state.DryStore(self.root / dry_state.STATE).read().state['admissions'], [])
        self.launch.assert_not_called()

    def test_recorded_development_allowance_preserves_history_and_denies_bad_decision(self):
        decision_path=self.root/dry_state.DEVELOPMENT_DECISION
        decision_path.parent.mkdir(parents=True)
        decision=dict(actor_id=policy.OWNER_ID,scope=policy.LOCAL_WORKFLOW,
                      rolling_limit=policy.LOCAL_DEVELOPMENT_LIMIT,campaign_limit=policy.LOCAL_CAMPAIGN_LIMIT,campaign='c-development-20261028',
                      authorization_text='Synthetic owner permission for quota tests')
        decision_path.write_text(json.dumps(decision))
        before=dry_state.DryStore(self.root/dry_state.STATE).read().state
        receipt=dry_state.reserve(self.root,'synthetic-adapter',c.APPROVED)
        after=dry_state.DryStore(self.root/dry_state.STATE).read().state
        self.assertEqual(receipt['rolling_limit'],policy.LOCAL_DEVELOPMENT_LIMIT)
        self.assertEqual(receipt['campaign_limit'],policy.LOCAL_CAMPAIGN_LIMIT)
        self.assertEqual(after['decisions'][:len(before['decisions'])],before['decisions'])
        self.assertEqual(after['admissions'][:len(before['admissions'])],before['admissions'])
        self.assertFalse(after['posting_enabled'])
        for alteration in ({'actor_id':1},{'scope':policy.TRIAGE_WORKFLOW},{'rolling_limit':policy.LOCAL_DEVELOPMENT_LIMIT+1},
                           {'campaign_limit':policy.LOCAL_CAMPAIGN_LIMIT+1},
                           {'campaign':'reset'},{'authorization_text':''}):
            decision_path.write_text(json.dumps({**decision,**alteration}))
            with self.assertRaises(policy.AdmissionDenied):
                dry_state.reserve(self.root,'rejected-adapter',c.APPROVED)
        decision_path.write_text('{malformed')
        with self.assertRaises(policy.AdmissionDenied):
            dry_state.reserve(self.root,'malformed-adapter',c.APPROVED)
        self.assertEqual(dry_state.DryStore(self.root/dry_state.STATE).read().state,after)
        self.launch.assert_not_called()
        self.network.assert_not_called()

    def test_invalid_selected_case_output_has_correct_identity_and_no_public_write(self):
        self.raw='not JSON'
        code,folder,record=self.run_case(20606)
        self.assertEqual((code,record['status']),(1,'invalid_output'))
        route=json.loads((folder/'validation.json').read_text())
        self.assertEqual(route['source_issue'],20606)
        self.assertEqual(route['public_actions'],[])
        self.assertIsNone(route['preview_comment'])
        self.assertFalse(record['posting_available'])
        self.network.assert_not_called()
