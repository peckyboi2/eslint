"""Offline complete-tree and corruption tests in a disposable local clone/copy."""

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_submission as verifier
import check_v9_attacks as attacks
from clarifier.shared.errors import ClarifierError


class SupplementalAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        (self.folder / "reservations").mkdir()
        self.plan = dict(attempt_limit=3, retries=0, campaign_id="test", actor_id=234542779,
                         cases=[dict(slot=i, run_id=f"test-{i}", attack=f"attack-{i}",
                                     input_hashes={"body.md": "a" * 64}) for i in range(1, 4)])

    def test_supplement_duplicate_cannot_consume_or_rewrite_another_slot(self):
        row = self.plan["cases"][0]
        attacks.reserve_slot(self.folder, self.plan, row)
        saved = (self.folder / "reservations/01.json").read_bytes()
        with self.assertRaises(ValueError):
            attacks.reserve_slot(self.folder, self.plan, row)
        self.assertEqual((self.folder / "reservations/01.json").read_bytes(), saved)
        self.assertEqual(len(list((self.folder / "reservations").glob("*.json"))), 1)

    def test_supplement_out_of_order_attempt_is_denied_without_reservation(self):
        with self.assertRaises(ValueError):
            attacks.reserve_slot(self.folder, self.plan, self.plan["cases"][1])
        self.assertEqual(list((self.folder / "reservations").glob("*.json")), [])

    def test_supplement_three_reservations_exhaust_the_allowance(self):
        for row in self.plan["cases"]:
            attacks.reserve_slot(self.folder, self.plan, row)
        with self.assertRaises(ValueError):
            attacks.reserve_slot(self.folder, self.plan, self.plan["cases"][-1])
        self.assertEqual(len(list((self.folder / "reservations").glob("*.json"))), 3)

    def test_supplement_larger_budget_is_denied(self):
        self.plan["attempt_limit"] = 4
        with self.assertRaises(ValueError):
            attacks.reserve_slot(self.folder, self.plan, self.plan["cases"][0])


class SubmissionVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy_context = verifier.disposable_copy(verifier.ROOT)
        cls.root = cls.copy_context.__enter__()
        cls.addClassCleanup(cls.copy_context.__exit__, None, None, None)

    @contextmanager
    def altered(self, name, data=None):
        path = self.root / name
        original = path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            path.unlink()
        else:
            path.write_bytes(data)
        try:
            yield path
        finally:
            if path.is_symlink() or (path.exists() and original is None):
                path.unlink()
            if original is not None:
                path.write_bytes(original)

    def rejected(self):
        with self.assertRaises((ValueError, ClarifierError)):
            verifier.verify(self.root)

    def test_complete_tree_passes_with_recorded_failure(self):
        result = verifier.verify(self.root)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["decision_matches"], {"count": 9, "denominator": 10})
        self.assertEqual(result["retained_failed_case"], 19924)
        self.assertEqual(result["final_frozen_files"], 168)
        self.assertEqual(result["preserved_earlier_evidence_files"], 2710)
        self.assertEqual(result["byte_identical_exports"], 66)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["supplemental_v9_attacks"]["actual_attempts"], 3)
        self.assertEqual(result["supplemental_v9_attacks"]["passes"], 3)
        self.assertEqual(result["supplemental_v9_attacks"]["previous_reservations_unchanged"], 51)

    def test_documented_cli_works_from_outside_checkout(self):
        result = subprocess.run([sys.executable, "-B", str(self.root / "scripts/verify_submission.py")],
                                cwd=self.root.parent, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["exact_final_comparison_reproduced"])

    def test_frozen_safety_suite_runs_without_changing_source_checkout(self):
        before = {name: verifier.historical.digest(self.root / name) for name in verifier.tree_files(self.root)}
        result = subprocess.run([sys.executable, "-B", str(self.root / "scripts/verify_submission.py"), "--safety-tests"],
                                cwd=self.root.parent, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 172 tests", result.stderr)
        after = {name: verifier.historical.digest(self.root / name) for name in verifier.tree_files(self.root)}
        self.assertEqual(before, after)

    def test_original_inputs_expectations_skill_and_source_cannot_change(self):
        for name in ("evals/golden/prepared-inputs/inputs/19924/body.md",
                     "evals/golden/expectations.json", "evals/golden/README.md",
                     ".claude/skills/eslint-clarification/SKILL.md",
                     "scripts/clarifier/inference/staging.py", "AGENTS.md",
                     "scripts/verify_baseline.py", "lib/linter/linter.js"):
            with self.subTest(path=name), self.altered(name, b"changed\n"):
                self.rejected()

    def test_original_freezes_and_preservation_inventory_cannot_change(self):
        for name in ("evals/golden/FREEZE.json", f"{verifier.FINAL}/freeze.json", verifier.G_PRESERVED):
            with self.subTest(path=name), self.altered(name, b"{}\n"):
                self.rejected()

    def test_results_failed_comparisons_and_archives_cannot_change(self):
        for name in ("evals/runs/final-f-20261028-v9-03-19924-a1/raw-output.txt",
                     f"{verifier.FINAL}/comparison.json", f"{verifier.FINAL}/comparisons/19924.json",
                     "evals/runs/20261028T050356Z-3f74565e/comparison.json",
                     "evals/checks/gate-g-20261028/full-tree-baseline.txt",
                     "evals/development-evidence.tar.gz"):
            with self.subTest(path=name), self.altered(name, b"changed\n"):
                self.rejected()

    def test_v9_supplement_inputs_requests_results_and_quota_cannot_change(self):
        folder = str(attacks.FOLDER)
        attempt = folder + "/attempts/v9-attacks-20261029-01-fabricated-approval-a1"
        for name in (folder + "/plan.json", folder + "/SHA256-MANIFEST.json",
                     folder + "/review.json", folder + "/reservations/01.json",
                     attempt + "/input/body.md", attempt + "/request.json",
                     attempt + "/raw-output.txt", attempt + "/loader.json",
                     "scripts/check_v9_attacks.py"):
            with self.subTest(path=name), self.altered(name, b"changed\n"):
                self.rejected()

    def test_v9_supplement_cannot_hide_missing_or_extra_attempt_evidence(self):
        folder = str(attacks.FOLDER)
        attempt = folder + "/attempts/v9-attacks-20261029-03-simulated-tool-instructions-a1"
        with self.altered(attempt + "/transcript.jsonl"):
            self.rejected()
        with self.altered(folder + "/reservations/04.json", b"{}\n"):
            self.rejected()

    def test_corrupt_and_missing_exports_are_rejected(self):
        name = f"{verifier.BUNDLE}/final/final-f-20261028-v9-03-19924-a1/raw-output.txt"
        with self.altered(name, b'{"decision":"human_review"}\n'):
            self.rejected()
        with self.altered(name):
            self.rejected()

    def test_rewriting_export_manifest_cannot_hide_removed_export(self):
        name = f"{verifier.BUNDLE}/exports.json"
        manifest = verifier.read_json(self.root / name)
        manifest["exports"].pop(next(iter(manifest["exports"])))
        with self.altered(name, json.dumps(manifest).encode()):
            self.rejected()

    def test_answers_cannot_enter_staged_input_packages(self):
        package = verifier.packages.load(19924, self.root)
        with self.altered("evals/golden/prepared-inputs/inputs/19924/answer.json", b"{}\n"):
            self.rejected()
            with tempfile.TemporaryDirectory(dir="/private/tmp") as destination:
                with self.assertRaises(ClarifierError):
                    verifier.staging.stage(package.source, Path(destination) / "input", expected=package.hashes)

    def test_ignored_unlisted_evidence_is_not_silently_skipped(self):
        with self.altered("evals/runs/unlisted-answer.txt", b"answer\n"):
            self.rejected()

    def test_missing_inherited_workflow_is_rejected(self):
        with self.altered(".github/workflows/ci.yml"):
            self.rejected()

    def test_broken_current_navigation_is_rejected(self):
        name = "evals/README.md"
        with self.altered(name, (self.root / name).read_bytes() + b"\n[missing](not-present.json)\n"):
            self.rejected()

    def test_design_line_limit_is_enforced(self):
        with self.altered("DESIGN.md", b"# Design\n" * 151):
            self.rejected()

    def test_current_command_cannot_disappear_from_submission_index(self):
        name = "evals/golden/INDEX.md"
        data = (self.root / name).read_bytes().replace(b"python3 -B scripts/verify_submission.py", b"obsolete-command")
        with self.altered(name, data):
            self.rejected()

    def test_export_checkout_byte_protection_is_required(self):
        with self.altered(f"{verifier.BUNDLE}/.gitattributes", b"* text=auto\n"):
            self.rejected()

    def test_export_symlink_is_rejected(self):
        name = f"{verifier.BUNDLE}/checks/pre-freeze-tests-v3.txt"
        with self.altered(name) as path:
            path.symlink_to(self.root / verifier.FINAL / "pre-freeze-tests-v3.txt")
            self.rejected()

    def test_cli_returns_failure_for_changed_fixture(self):
        with self.altered(f"{verifier.BUNDLE}/checks/comparison.json", b"{}\n"):
            result = subprocess.run([sys.executable, "-B", str(self.root / "scripts/verify_submission.py")],
                                    cwd=self.root, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 1)
            self.assertIn("FAIL:", result.stderr)


if __name__ == "__main__":
    unittest.main()
