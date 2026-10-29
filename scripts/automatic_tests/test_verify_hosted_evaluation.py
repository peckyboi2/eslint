"""Corruption checks for genuine saved current hosted correctness evidence; no model."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import verify_automatic as automatic
import verify_hosted_evaluation as evaluation
import verify_submission as submission


class HostedEvaluationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy=submission.disposable_copy(submission.ROOT)
        cls.root=cls.copy.__enter__()
        cls.addClassCleanup(cls.copy.__exit__,None,None,None)
        cls.candidate=automatic.read_json(cls.root/automatic.HOSTED_CANDIDATE)

    @contextmanager
    def altered(self,name,data):
        path=self.root/name;original=path.read_bytes()
        try:
            if data is None:path.unlink()
            else:path.write_bytes(data)
            yield
        finally:path.write_bytes(original)

    def verify(self,reference=None):
        return evaluation.verify(self.root,reference or self.candidate['observed_current_evaluation'],self.candidate['configuration'])

    def test_all_thirteen_original_hosted_attempts_are_verified(self):
        result=self.verify()
        self.assertTrue(result['evaluated'])
        self.assertEqual(result['provider_calls'],13)
        self.assertEqual(result['historical_total'],10)
        self.assertEqual(result['adversarial_total'],3)
        self.assertEqual(result['normal_window_restored_seconds'],86400)
        self.assertEqual(result['tool_calls'],0)
        self.assertEqual(result['public_actions'],0)

    def test_missing_hidden_skill_is_rejected(self):
        name=evaluation.FOLDER/'slots/01-20373/artifacts/attempt/configuration/.claude/skills/eslint-clarification/SKILL.md'
        with self.altered(name,None),self.assertRaises(ValueError):self.verify()

    def test_changed_provider_output_is_rejected(self):
        name=evaluation.FOLDER/'slots/01-20373/artifacts/attempt/raw-output.txt'
        with self.altered(name,b'{}'),self.assertRaises(ValueError):self.verify()

    def test_inflated_summary_cannot_override_actual_outputs(self):
        reference=copy.deepcopy(self.candidate['observed_current_evaluation'])
        summary=automatic.read_json(self.root/evaluation.SUMMARY)
        summary['aggregate']['historical_matches']=11
        raw=json.dumps(summary).encode();reference['sha256']=evaluation.sha(raw)
        with self.altered(evaluation.SUMMARY,raw),self.assertRaisesRegex(ValueError,'saved comparison'):self.verify(reference)

    def test_unrestored_temporary_window_is_rejected(self):
        name=evaluation.CAMPAIGN/'restoration.json'
        value=automatic.read_json(self.root/name);value['variable_receipt']['value']='60'
        with self.altered(name,json.dumps(value).encode()),self.assertRaisesRegex(ValueError,'not restored'):self.verify()

    def test_removed_prior_smoke_reservation_is_rejected(self):
        import base64
        name=evaluation.CAMPAIGN/'state-after.json'
        receipt=automatic.read_json(self.root/name);state=json.loads(base64.b64decode(receipt['content']))
        state['admissions']=state['admissions'][1:]
        receipt['content']=base64.b64encode(json.dumps(state).encode()).decode()
        with self.altered(name,json.dumps(receipt).encode()),self.assertRaisesRegex(ValueError,'reservation history'):self.verify()


if __name__=='__main__':unittest.main()
