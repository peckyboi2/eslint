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
        self.assertEqual(result['current_candidate']['evaluated'],'observed_current_evaluation' in self.candidate())
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
        candidate.pop('observed_current_evaluation',None)
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

    def test_manifest_cannot_depend_on_ignored_local_bytecode(self):
        candidate=self.candidate()
        candidate['files']['scripts/clarifier/__pycache__/local.pyc']='0'*64
        with self.assertRaisesRegex(ValueError,'bytecode'):
            automatic.verify_candidate_scope(candidate)

    def test_stop_evidence_packaging_does_not_allow_other_run_changes(self):
        candidate=dict(version=automatic.HOSTED_VERSION,files={
            '.gitignore':'0'*64,
            'evals/runs/stop-workflow-20261030-runs-41017826713-41018317883/PACKAGE-SHA256.json':'0'*64})
        automatic.verify_candidate_scope(candidate)
        candidate['version']=automatic.LEGACY_VERSION
        with self.assertRaisesRegex(ValueError,'Candidate scope'):
            automatic.verify_candidate_scope(candidate)
        candidate['version']=automatic.HOSTED_VERSION
        candidate['files']['evals/runs/unapproved/record.json']='0'*64
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

    def test_retired_plan_is_preserved_in_historical_replay(self):
        name='evals/golden/evaluation-plan.md'
        retired=automatic.verify_retired_documents(self.root,self.candidate())
        self.assertEqual(retired,{name:automatic.RETIRED_DOCUMENTS[name]})
        with automatic.historical_projection(self.root) as historical:
            self.assertEqual(automatic.sha((historical/name).read_bytes()),retired[name])

    def test_other_evidence_cannot_be_retired(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_documents']['evals/golden/expectations.json']='0'*64
        with self.assertRaisesRegex(ValueError,'Unapproved document retirement'):
            automatic.verify_retired_documents(self.root,candidate)

    def test_retired_document_hash_cannot_be_relabelled(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_documents']['evals/golden/evaluation-plan.md']='0'*64
        with self.assertRaisesRegex(ValueError,'Retired document Git hash differs'):
            automatic.verify_retired_documents(self.root,candidate)

    def test_removal_requires_explicit_manifest_record(self):
        candidate=copy.deepcopy(self.candidate())
        candidate.pop('retired_documents')
        with self.assertRaisesRegex(ValueError,'Missing candidate/evidence: evals/golden/evaluation-plan.md'):
            automatic.verify_originals(self.root,candidate)

    def test_retired_platform_records_remain_verifiable_in_git(self):
        retired={name:digest for name,digest in automatic.verify_retired_directories(self.root,self.candidate()).items()
                 if name.startswith('evals/platform-tests/')}
        self.assertEqual(len(retired),874)
        with automatic.historical_projection(self.root) as historical:
            self.assertTrue(all(automatic.sha((historical/name).read_bytes())==digest
                                for name,digest in retired.items()))

    def test_current_results_cannot_be_retired_as_a_directory(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_directories']['evals/golden/hosted-v11-20261029']='0'*40
        with self.assertRaisesRegex(ValueError,'Unapproved directory retirement'):
            automatic.verify_retired_directories(self.root,candidate)

    def test_retired_directory_hash_cannot_be_relabelled(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_directories']['evals/platform-tests']='0'*40
        with self.assertRaisesRegex(ValueError,'Retired directory Git tree differs'):
            automatic.verify_retired_directories(self.root,candidate)

    def test_directory_removal_requires_explicit_manifest_record(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_directories'].pop('evals/platform-tests')
        with self.assertRaisesRegex(ValueError,'Missing candidate/evidence: evals/platform-tests/'):
            automatic.verify_originals(self.root,candidate)

    def test_retired_development_runs_remain_verifiable_in_git(self):
        retired={name:digest for name,digest in automatic.verify_retired_directories(self.root,self.candidate()).items()
                 if name.startswith('evals/runs/')}
        self.assertEqual(len(retired),747)
        self.assertEqual({Path(name).parts[2] for name in retired},automatic.RETIRED_RUNS)
        with automatic.historical_projection(self.root) as historical:
            self.assertTrue(all(automatic.sha((historical/name).read_bytes())==digest
                                for name,digest in retired.items()))

    def test_failed_run_cannot_be_retired(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_directories']['evals/runs/20261028T044906Z-2dbe7936']='0'*40
        with self.assertRaisesRegex(ValueError,'Unapproved directory retirement'):
            automatic.verify_retired_directories(self.root,candidate)

    def test_retired_run_hash_cannot_be_relabelled(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_directories']['evals/runs/20261028T014605Z-7eb7cc4d']='0'*40
        with self.assertRaisesRegex(ValueError,'Retired directory Git tree differs'):
            automatic.verify_retired_directories(self.root,candidate)

    def test_run_removal_requires_explicit_manifest_record(self):
        candidate=copy.deepcopy(self.candidate())
        candidate['retired_directories'].pop('evals/runs/20261028T014605Z-7eb7cc4d')
        with self.assertRaisesRegex(ValueError,'Missing candidate/evidence: evals/runs/20261028T014605Z-7eb7cc4d/'):
            automatic.verify_originals(self.root,candidate)


if __name__=='__main__':
    unittest.main()
