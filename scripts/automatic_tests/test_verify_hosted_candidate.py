"""Offline hosted-candidate preservation and identity checks; no inference. Serves H01."""
from contextlib import contextmanager
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import verify_automatic as automatic
import verify_submission as submission


class HostedCandidateVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy=submission.disposable_copy(submission.ROOT)
        cls.root=cls.copy.__enter__()
        cls.addClassCleanup(cls.copy.__exit__,None,None,None)

    @contextmanager
    def altered(self,name: str,data: bytes | None):
        """Temporarily change a disposable path, restoring original bytes on exit."""
        path=self.root/name
        original=path.read_bytes()
        if data is None:
            path.unlink()
        else:
            path.write_bytes(data)
        try:
            yield
        finally:
            path.write_bytes(original)

    def candidate(self) -> dict:
        """Return the active test manifest without mutating saved metadata."""
        return automatic.read_json(self.root/automatic.HOSTED_CANDIDATE)

    def test_hosted_preparation_preserves_score_and_exhausted_reservations(self):
        result=automatic.verify(self.root)
        self.assertEqual(result['current_candidate']['version'],'hosted-preview-v11-artifacts-v2')
        self.assertEqual(result['current_candidate']['manifest_path'],'evals/hosted-v11/candidate.json')
        self.assertFalse(result['current_candidate']['evaluated'])
        self.assertEqual(result['current_candidate']['hosted'],'observed_current_hosted_smoke' in self.candidate())
        self.assertEqual(result['decision_matches'],{'count':9,'denominator':10})
        self.assertEqual(result['retained_failed_case'],19924)
        self.assertEqual(result['v10_preserved']['previous_reservations_unchanged'],54)
        self.assertEqual(result['v10_preserved']['preserved_metadata_files'],33)
        self.assertEqual(result['model_calls'],0)

    def test_incomplete_new_preparation_cannot_fall_back_to_old_candidate(self):
        with self.altered(automatic.HOSTED_CANDIDATE,None):
            with self.assertRaises(ValueError):
                automatic.verify(self.root)

    def test_superseded_candidate_bytes_cannot_be_rewritten(self):
        with self.altered(automatic.CANDIDATE,b'{}\n'):
            with self.assertRaisesRegex(ValueError,'Prior v10 evidence changed'):
                automatic.verify(self.root)

    def test_unexecuted_local_freeze_cannot_be_relabelled_as_hosted(self):
        with self.altered(automatic.FOLDER/'evaluation-freeze.json',b'{}\n'):
            with self.assertRaisesRegex(ValueError,'Prior v10 evidence changed'):
                automatic.verify(self.root)

    def test_previous_allowance_cannot_be_reset(self):
        name='evals/checks/gate-c-20261028/dry-state.json'
        with self.altered(name,b'{"admissions": []}\n'):
            with self.assertRaisesRegex(ValueError,'Consumed reservation changed'):
                automatic.verify(self.root)

    def test_source_hashes_are_not_a_new_accuracy_claim(self):
        candidate=self.candidate()
        candidate['evaluated']=True
        with self.assertRaisesRegex(ValueError,'Preparation manifest'):
            automatic.verify_hosted_configuration(self.root,candidate)

    def test_current_runtime_aggregate_must_match_every_configuration_byte(self):
        candidate=self.candidate()
        candidate['configuration']['aggregate_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'configuration aggregate'):
            automatic.verify_hosted_configuration(self.root,candidate)

    def test_current_runtime_inventory_cannot_omit_a_source(self):
        candidate=self.candidate()
        del candidate['configuration']['source_hashes']['scripts/clarifier/inference/hosted_runtime.py']
        with self.assertRaisesRegex(ValueError,'configuration inventory'):
            automatic.verify_hosted_configuration(self.root,candidate)

    def test_manifest_cannot_authorise_inherited_source_changes(self):
        candidate=self.candidate()
        candidate['files']['lib/cli.js']='0'*64
        with self.assertRaisesRegex(ValueError,'Candidate scope'):
            automatic.verify_candidate_scope(candidate)

    def test_guide_updates_are_allowed_only_in_the_current_candidate(self):
        candidate=dict(version=automatic.HOSTED_VERSION,
                       files={'AGENTS.md':'0'*64,'CONTRIBUTING.md':'0'*64})
        automatic.verify_candidate_scope(candidate)
        candidate['version']=automatic.LEGACY_VERSION
        with self.assertRaisesRegex(ValueError,'Candidate scope'):
            automatic.verify_candidate_scope(candidate)

    def test_reviewed_guides_reject_later_unrecorded_edits(self):
        for name in ('AGENTS.md','CONTRIBUTING.md'):
            with self.subTest(guide=name), self.altered(name,b'unreviewed guide change\n'):
                with self.assertRaisesRegex(ValueError,'Candidate hash mismatch: '+name):
                    automatic.verify(self.root)

    def test_old_candidate_does_not_authorise_new_hosted_directory(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['version']=automatic.LEGACY_VERSION
        with self.assertRaisesRegex(ValueError,'Candidate scope'):
            automatic.verify_candidate_scope(candidate)

    def test_exact_review_hash_binds_the_active_manifest(self):
        with self.assertRaisesRegex(ValueError,'Candidate review hash'):
            automatic.verify(self.root,'0'*64)


if __name__=='__main__':
    unittest.main()
