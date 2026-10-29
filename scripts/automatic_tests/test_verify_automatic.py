"""Offline v10 corruption checks; no provider, GitHub or report execution. Serves C04."""
from contextlib import contextmanager
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import verify_automatic as automatic
import verify_submission as submission


class AutomaticVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy=submission.disposable_copy(submission.ROOT)
        cls.root=cls.copy.__enter__()
        cls.addClassCleanup(cls.copy.__exit__,None,None,None)

    @contextmanager
    def altered(self,name: str,data: bytes):
        """Temporarily change a disposable file, retaining original bytes."""
        path=self.root/name
        old=path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        try:
            yield
        finally:
            if old is None: path.unlink()
            else: path.write_bytes(old)

    def test_old_and_new_are_distinct(self):
        result=automatic.verify(self.root)
        self.assertEqual(result['decision_matches'],{'count':9,'denominator':10})
        self.assertEqual(result['v9_baseline']['frozen_git_files'],168)
        self.assertFalse(result['current_candidate']['evaluated'])
        self.assertFalse(result['current_candidate']['hosted'])
        self.assertEqual(result['model_calls'],0)

    def test_candidate_source_corruption_rejected(self):
        with self.altered('scripts/clarifier/inference/live_snapshot.py',b'changed\n'):
            with self.assertRaises(ValueError): automatic.verify(self.root)

    def test_preexisting_overlay_corruption_rejected(self):
        with self.altered('evals/automatic-v10/baseline-overlay/scripts/verify_submission.py',b'changed\n'):
            with self.assertRaises(ValueError): automatic.verify(self.root)

    def test_unlisted_file_rejected(self):
        with self.altered('evals/automatic-v10/hidden-answer.txt',b'answer\n'):
            with self.assertRaises(ValueError): automatic.verify(self.root)

    def test_external_candidate_review_hash_is_exact(self):
        with self.assertRaises(ValueError): automatic.verify(self.root,'0'*64)

    def test_original_failed_output_corruption_rejected(self):
        with self.altered('evals/runs/final-f-20261028-v9-03-19924-a1/raw-output.txt',b'changed\n'):
            with self.assertRaises(ValueError): automatic.verify(self.root)
