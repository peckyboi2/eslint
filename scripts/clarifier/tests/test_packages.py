"""Task 29 package fidelity/isolation checks; no inference or public writes."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from clarifier.shared import constants as c
from clarifier.shared.errors import StagingError
from clarifier.inference import packages, recording, request, staging


class HistoricalPackages(unittest.TestCase):
    def test_all_packages_preserve_complete_bytes_cutoffs_and_selected_input_only(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as tmp:
            for issue in c.HISTORICAL_CASE_IDS:
                with self.subTest(issue=issue):
                    package = packages.load(issue)
                    session = recording.start_run(True, Path(tmp), id_factory=lambda: str(issue))
                    session.config = recording.load_configuration(c.ROOT / c.CONFIG_PATH)
                    try:
                        staged = staging.prepare(session, package)
                        text = request.prepare(session, staged)
                        files = json.loads(text.split('\n', 1)[1])['files']
                        self.assertEqual(set(files), set(package.hashes))
                        self.assertEqual(staged.manifest['staged_bytes'], package.total_bytes)
                        self.assertLessEqual(package.total_bytes, c.MAX_INPUT_BYTES)
                        self.assertEqual(session.record['source_issue'], issue)
                        self.assertEqual(session.record['historical_cutoff'], package.cutoff)
                        for name, digest in package.hashes.items():
                            self.assertEqual(recording.sha(files[name].encode()), digest)
                            self.assertEqual((package.source / name).read_bytes(), (staged.evidence / name).read_bytes())
                        actual = {p.relative_to(staged.workspace).as_posix()
                                  for p in staged.workspace.rglob('*') if p.is_file()}
                        self.assertEqual(actual, {'evidence/' + name for name in package.hashes})
                        for excluded in ('expected_decision', 'review_rationale', 'later-discussion', '.git/'):
                            self.assertNotIn(excluded, text)
                        self.assertEqual(session.record['public_actions'], [])
                        self.assertFalse(session.record['posting_available'])
                    finally:
                        staging.cleanup(session)

    def test_special_provenance_and_support_are_unchanged(self):
        weak = packages.load(19818)
        self.assertEqual(weak.cutoff['kind'], 'opening_record_via_clickhouse')
        self.assertIn('i++', (weak.source / 'body.md').read_text())
        self.assertIn('i--', (weak.source / 'body.md').read_text())
        for issue in (19847, 19118):
            package = packages.load(issue)
            self.assertTrue(any(name.startswith('support/') for name in package.hashes))
        for issue in (20373, 20606, 21304):
            self.assertEqual(packages.load(issue).cutoff['kind'], 'early_pre_response_snapshot')

    def test_unapproved_identifiers_and_catalog_changes_fail_closed(self):
        for issue in (True, '20606', 99999, '../20606'):
            with self.subTest(issue=issue), self.assertRaises(StagingError):
                packages.load(issue)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / c.PREPARED_PATH
            target.mkdir(parents=True)
            for name in (c.PACKAGE_MANIFEST, c.PACKAGE_HASHES):
                shutil.copy2(c.ROOT / c.PREPARED_PATH / name, target / name)
            (target / c.PACKAGE_MANIFEST).write_text('{}')
            with self.assertRaises(StagingError):
                packages.load(20606, root)

    def test_nested_support_missing_extra_symlink_and_aggregate_size_are_rejected(self):
        package = packages.load(19118)
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as tmp:
            root = Path(tmp)
            source = root / 'source'
            shutil.copytree(package.source, source)
            with self.assertRaises(StagingError):
                staging.stage(source, root / 'size', package.total_bytes - 1, expected=package.hashes)
            extra = source / 'support/expected.json'
            extra.write_text('evaluator-only')
            with self.assertRaises(StagingError):
                staging.stage(source, root / 'extra', expected=package.hashes)
            extra.unlink()
            support = source / 'support/README.md'
            support.unlink()
            with self.assertRaises(StagingError):
                staging.stage(source, root / 'missing', expected=package.hashes)
            support.symlink_to(c.ROOT / 'evals/golden/expectations.json')
            with self.assertRaises(StagingError):
                staging.stage(source, root / 'symlink', expected=package.hashes)
            support.unlink()
            (source / 'support').rename(source / 'hidden-support')
            (source / 'support').symlink_to(source / 'hidden-support', target_is_directory=True)
            with self.assertRaises(StagingError):
                staging.stage(source, root / 'parent-symlink', expected=package.hashes)

    def test_snapshot_binding_and_unsafe_manifest_paths_fail_closed(self):
        package = packages.load(20606)
        snapshot = json.loads((package.source / 'snapshot.json').read_text())
        row = {'issue': package.issue, 'body_sha256': package.hashes['body.md'],
               'cutoff_kind': package.cutoff['kind'], 'cutoff_utc': 'changed'}
        with self.assertRaises(StagingError):
            packages.verify_snapshot(row, snapshot, package.hashes)
        for name in ('../secret', '/secret', 'x/../secret', 'x\\secret'):
            entries = {'inputs/20606/' + name: '0' * 64}
            with self.subTest(name=name), self.assertRaises(StagingError):
                packages.select_hashes(entries, 'inputs/20606')
