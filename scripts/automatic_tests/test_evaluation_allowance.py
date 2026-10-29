"""Synthetic new-allowance tests; never approve or call any provider. Serves D01."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import evaluate_automatic as evaluator
from clarifier.shared.errors import ClarifierError


class EvaluationAllowanceTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((evaluator.ROOT/evaluator.PLAN).read_text())
        self.temp=self.enterContext(tempfile.TemporaryDirectory(dir='/private/tmp'))
        self.folder=Path(self.temp)

    def test_original_order_and_expectations_are_fixed(self):
        evaluator.check_plan(self.plan)
        self.plan['cases'][2]['expected_decision']='no_action'
        with self.assertRaises(ClarifierError): evaluator.check_plan(self.plan)

    def test_larger_allowance_rejected(self):
        self.plan['new_attempt_limit']=14
        with self.assertRaises(ClarifierError): evaluator.reserve_slot(self.folder,self.plan,self.plan['cases'][0],at='synthetic')
        self.assertFalse((self.folder/'reservations').exists())

    def test_duplicate_and_out_of_order_have_no_provider_effect(self):
        with patch.object(evaluator.transport,'prepare_engine') as model:
            with self.assertRaises(ClarifierError): evaluator.reserve_slot(self.folder,self.plan,self.plan['cases'][1],at='synthetic')
            evaluator.reserve_slot(self.folder,self.plan,self.plan['cases'][0],at='synthetic')
            with self.assertRaises(ClarifierError): evaluator.reserve_slot(self.folder,self.plan,self.plan['cases'][0],at='synthetic')
        model.assert_not_called()
        self.assertEqual(len(list((self.folder/'reservations').iterdir())),1)

    def test_all_thirteen_consumed_slots_cannot_be_reused(self):
        for row in self.plan['cases']: evaluator.reserve_slot(self.folder,self.plan,row,at='synthetic')
        with self.assertRaises(ClarifierError): evaluator.reserve_slot(self.folder,self.plan,self.plan['cases'][-1],at='synthetic')
        self.assertEqual(len(list((self.folder/'reservations').iterdir())),13)

    def test_missing_or_mismatched_owner_approval_is_silent(self):
        with patch.object(evaluator.transport,'prepare_engine') as model:
            with self.assertRaises(ClarifierError): evaluator.check_approval({},self.plan,'a'*64,'b'*64)
        model.assert_not_called()

    def test_failed_prior_attempt_stops_continuation(self):
        with self.assertRaises(ClarifierError): evaluator.require_previous_completed(self.folder,self.plan,2)

    def test_binary_evidence_is_hashed_without_utf8_decoding(self):
        raw=b'\x1f\x8b\xffretained binary evidence'
        (self.folder/'evidence.gz').write_bytes(raw)
        evaluator.verify_files(self.folder,{'evidence.gz':evaluator.recording.sha(raw)})
        with self.assertRaises(ClarifierError): evaluator.verify_files(self.folder,{'evidence.gz':'a'*64})
