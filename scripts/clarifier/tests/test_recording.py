"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import constants as c
import errors
import recording as rec

spec = importlib.util.spec_from_file_location("verify_baseline", c.ROOT / "scripts/verify_baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class DevelopmentEvidence(unittest.TestCase):
    def make_bundle(self, path, payload, expected_hash=None):
        import hashlib
        import io
        import tarfile
        manifest = {'files': {'output.txt': expected_hash or hashlib.sha256(payload).hexdigest()}}
        with tarfile.open(path, 'w:gz') as archive:
            for name, data in [('output.txt', payload), ('manifest.json', json.dumps(manifest).encode())]:
                item = tarfile.TarInfo(name)
                item.size = len(data)
                archive.addfile(item, io.BytesIO(data))

    def test_data_bundle_verifies_without_old_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.tar.gz'
            self.make_bundle(path, b'preserved failed output')
            self.assertEqual(baseline.check_evidence_archive(path), 1)
            self.assertEqual(baseline.check_evidence_archive(Path(tmp) / 'absent.tar.gz'), 0)

    def test_changed_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.tar.gz'
            self.make_bundle(path, b'changed output', expected_hash='0' * 64)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                baseline.check_evidence_archive(path)


class ConfigurationIdentity(unittest.TestCase):
    def test_records_code_hashes_without_copying_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            identity = rec.record_configuration(folder)
            manifest = json.loads((folder / c.CONFIGURATION_HASHES_FILE).read_text())
            self.assertEqual(set(manifest['files']), {p.as_posix() for p in c.RETAINED_CONFIG_PATHS})
            self.assertEqual(set(manifest['source_hashes']), {p.as_posix() for p in c.CONFIG_PATHS if p not in c.RETAINED_CONFIG_PATHS})
            self.assertFalse(list(folder.rglob('*.py')))
            rec.save_json(folder / 'record.json', {'configuration_sha256': identity})
            baseline.check_configuration(folder)
            self.assertEqual(json.loads((folder / 'configuration' / c.CONFIG_PATH).read_text())['model'], c.FIXED_CONFIG['model'])

    def test_changed_source_identifier_breaks_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            identity = rec.record_configuration(folder)
            rec.save_json(folder / 'record.json', {'configuration_sha256': identity})
            path = folder / c.CONFIGURATION_HASHES_FILE
            manifest = json.loads(path.read_text())
            name = next(iter(manifest['source_hashes']))
            manifest['source_hashes'][name] = '0' * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'aggregate'):
                baseline.check_configuration(folder)

    def test_python_sources_are_rejected_from_data_bundle(self):
        import io
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.tar.gz'
            with tarfile.open(path, 'w:gz') as archive:
                item = tarfile.TarInfo('preview.py')
                item.size = 4
                archive.addfile(item, io.BytesIO(b'code'))
            with self.assertRaisesRegex(ValueError, 'data files only'):
                baseline.check_evidence_archive(path)


class ImmutableRecords(unittest.TestCase):
    def test_configuration_snapshots_are_exclusive(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "record.json"
            rec.save_json(path, {"status": "failed"})
            with self.assertRaises(errors.RecordingError):
                rec.save_json(path, {"status": "completed"})
            self.assertEqual(json.loads(path.read_text())["status"], "failed")


class RecordingPolicy(unittest.TestCase):
    def test_redaction_and_exclusive_evidence(self):
        value = {'Authorization': 'Bearer value', 'nested': {'access_token': 'secret'}, 'text': 'Bearer token'}
        self.assertEqual(rec.redact(value), {'Authorization': '[REDACTED]',
                         'nested': {'access_token': '[REDACTED]'}, 'text': 'Bearer [REDACTED]'})
        self.assertEqual(rec.redact_text('known-secret', ['known-secret']), '[REDACTED]')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.txt'
            rec.write_text(path, 'first')
            with self.assertRaises(errors.RecordingError):
                rec.write_text(path, 'second')
            self.assertEqual(path.read_text(), 'first')

    def test_injectable_identity_time_and_unknown_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = rec.start_run(True, root, lambda: 'fixed-time', lambda: 'fixed-id')
            self.assertEqual(session.record['started_at'], 'fixed-time')
            self.assertEqual(session.record['usage'], c.UNKNOWN)
            self.assertEqual(session.record['cost'], c.UNKNOWN)
            self.assertEqual(session.record['public_actions'], [])
            with self.assertRaises(errors.RecordingError):
                rec.start_run(True, root, lambda: 'fixed-time', lambda: 'fixed-id')
            for name in ('../escape', '.', '..', '/absolute'):
                with self.subTest(name=name), self.assertRaises(errors.RecordingError):
                    rec.start_run(True, root, id_factory=lambda: name)

    def test_missing_and_ambiguous_configuration_fail_closed(self):
        for value in (None, {}, {'posting': True}):
            with self.subTest(value=value), self.assertRaises(errors.ConfigurationError):
                rec.validate_configuration(value)
        with tempfile.TemporaryDirectory() as tmp:
            session = rec.start_run(True, Path(tmp), id_factory=lambda: 'missing')
            with self.assertRaises(errors.RecordingError):
                rec.configure(session)


class FailureEvidence(unittest.TestCase):
    def test_typed_failure_redacts_secrets_and_finishes_with_no_public_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = rec.start_run(True, Path(tmp), lambda: 'time', lambda: 'id')
            session.secrets = ['private-value']
            rec.fail(session, errors.TransportError('private-value'))
            rec.finish(session)
            record = json.loads((session.folder / 'record.json').read_text())
            self.assertEqual(record['status'], 'failed')
            self.assertEqual(record['errors'], ['[REDACTED]'])
            self.assertEqual(record['public_actions'], [])
            self.assertFalse(record['posting_available'])
            baseline.check_manifest(session.folder, baseline.read_json(session.folder / 'artifact-hashes.json'))

    def test_malformed_configuration_is_a_configuration_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            path.write_text('{')
            with self.assertRaises(errors.ConfigurationError):
                rec.load_configuration(path)
