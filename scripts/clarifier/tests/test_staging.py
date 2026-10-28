"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock

from clarifier.shared import constants as c
from clarifier.shared import errors
from clarifier.inference import recording as rec
from clarifier.inference import staging as stage


class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        shutil.copytree(c.ROOT / "evals/golden/prepared-inputs/inputs/20373", self.source)

    def test_exact_bytes_and_no_evaluator_material(self):
        manifest = stage.stage(self.source, self.root / "stage")
        self.assertEqual(set(manifest["staged_files"]), {"body.md", "title.txt", "snapshot.json"})
        self.assertEqual(manifest["staged_bytes"], 6253)
        for name in manifest["staged_files"]:
            self.assertEqual((self.source / name).read_bytes(), (self.root / "stage" / name).read_bytes())
        with self.assertRaises(errors.StagingError):
            stage.stage(self.source, self.root / "stage")

    def test_hash_size_and_extra_file_rejection(self):
        with self.assertRaises(ValueError):
            stage.stage(self.source, self.root / "stage", 4800)
        (self.source / "body.md").write_text("changed")
        with self.assertRaises(ValueError):
            stage.stage(self.source, self.root / "stage")
        (self.source / "expected.json").write_text("answer")
        with self.assertRaises(ValueError):
            stage.stage(self.source, self.root / "stage")

    def test_path_traversal_symlinks_and_special_files(self):
        for name in ("../secret", "/etc/passwd", "x/../body.md", "x\\body.md", "./body.md"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                stage.read_safe(self.source, name, 65536)
        body = self.source / "body.md"
        body.unlink()
        body.symlink_to(c.ROOT / "evals/golden/expectations.json")
        with self.assertRaises(ValueError):
            stage.stage(self.source, self.root / "stage")
        body.unlink()
        os.mkfifo(body)
        with self.assertRaises(ValueError):
            stage.stage(self.source, self.root / "stage")

    def test_symlink_parent_and_hardlink(self):
        link = self.root / "link"
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            stage.stage(link, self.root / "stage")
        os.link(self.source / "body.md", self.root / "extra-link")
        with self.assertRaises(ValueError):
            stage.stage(self.source, self.root / "stage")


class SourceVerification(unittest.TestCase):
    def test_hash_verification_rejects_missing_extra_or_changed_files(self):
        expected = {'body.md': rec.sha(b'original')}
        stage.verify_source_hashes({'body.md': b'original'}, expected)
        for files in ({}, {'body.md': b'changed'}, {'body.md': b'original', 'answer': b'x'}):
            with self.subTest(files=files), self.assertRaises(errors.StagingError):
                stage.verify_source_hashes(files, expected)

    def test_non_utf8_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / 'text').write_bytes(b'\xff')
            with self.assertRaises(errors.StagingError):
                stage.read_safe(source, 'text', c.MAX_INPUT_BYTES)


class CleanupFailure(unittest.TestCase):
    def test_cleanup_denial_stays_silent_and_records_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = rec.start_run(True, Path(tmp), id_factory=lambda: 'cleanup')
            session.temporary = Mock()
            session.temporary.cleanup.side_effect = OSError('Bearer private-value')
            stage.cleanup(session)
            self.assertEqual(session.record['status'], 'failed')
            self.assertEqual(session.record['public_actions'], [])
            self.assertFalse(session.record['posting_available'])
            self.assertEqual(session.record['errors'], ['Private workspace cleanup failed'])
