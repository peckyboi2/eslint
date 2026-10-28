"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from clarifier.shared import constants as c
from clarifier.shared import errors
from clarifier import preview as p
from clarifier.inference import recording as rec
from clarifier.inference import request as req
from clarifier.outputs import routing as route
from clarifier.inference import staging as stage
from clarifier.inference import transport as t

spec = importlib.util.spec_from_file_location("verify_baseline", c.ROOT / "scripts/verify_baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class RunFixture(unittest.TestCase):
    """Exercise complete runs with a fake CLI and transport; never call a model."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in c.CONFIG_PATHS:
            source = c.ROOT / name
            target = self.root / source.relative_to(c.ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        case = "evals/golden/prepared-inputs/inputs/20373"
        shutil.copytree(c.ROOT / case, self.root / case)
        here = self.root / "scripts/clarifier"
        self.config = json.loads((self.root / c.CONFIG_PATH).read_text())

        self.network = self.enterContext(patch.object(t.http.client, "HTTPSConnection"))
        self.binary = self.root / "synthetic-codex"
        self.binary.write_bytes(b"Synthetic binary; never executed.")
        self.enterContext(patch.object(t.shutil, "which", return_value=str(self.binary)))
        self.version = self.enterContext(patch.object(
            t.subprocess, "run", return_value=Mock(stdout=self.config["cli_version"] + "\n"),
        ))
        self.process = Mock(pid=12345, returncode=0)
        self.process.poll.return_value = 0
        self.launch = self.enterContext(patch.object(t.subprocess, "Popen", return_value=self.process))
        self.kill = self.enterContext(patch.object(t.os, "killpg"))
        self.gate = Mock(errors=[], attempts=1, completion={"usage": None, "model": "synthetic"})
        self.gate.start.return_value = "http://127.0.0.1:12345"
        self.gate_factory = self.enterContext(patch.object(t, "Gate", return_value=self.gate))
        self.raw = json.dumps({"decision": "no_action", "rationale": "Synthetic lifecycle fixture.",
                               "clarification": None})
        self.process.communicate.side_effect = self.complete_response

        self.login = self.root / "login"
        self.login.mkdir()
        self.auth = {"auth_mode": "chatgpt", "tokens": {"access_token": "synthetic-not-a-credential"}}
        (self.login / "auth.json").write_text(json.dumps(self.auth))
        self.enterContext(patch.dict(t.os.environ, {"CODEX_HOME": str(self.login)}))

    def complete_response(self, prompt, timeout):
        folder = self.gate_factory.call_args.args[0]
        self.assertEqual(prompt, (folder / "prompt.txt").read_bytes())
        self.assertEqual(timeout, self.config["runtime_limit_seconds"])
        engine_home = Path(self.launch.call_args.kwargs["env"]["CODEX_HOME"])
        platform_test = self.gate_factory.call_args.args[4]
        if platform_test:
            self.assertFalse((engine_home / "auth.json").exists())
        else:
            self.assertEqual(json.loads((engine_home / "auth.json").read_text()), self.auth)
            self.assertEqual((engine_home / "auth.json").stat().st_mode & 0o777, 0o600)
        (folder / "raw-output.txt").write_text(self.raw)

    def run_preview(self, platform_test=True):
        output = io.StringIO()
        with redirect_stdout(output):
            code = p.run(platform_test, root=self.root)
        summary = json.loads(output.getvalue())
        folder = Path(summary["folder"])
        record = json.loads((folder / "record.json").read_text())
        inventory = json.loads((folder / "artifact-hashes.json").read_text())
        baseline.check_manifest(folder, inventory)
        self.assertEqual(set(inventory), {path.relative_to(folder).as_posix()
                         for path in folder.rglob("*") if path.is_file()} - {"artifact-hashes.json"})
        self.assertFalse(Path(record["model_workspace"]).parent.exists())
        self.assertFalse(any(path.name == "auth.json" for path in folder.rglob("*")))
        self.assertEqual(record["public_actions"], [])
        self.assertFalse(record["posting_available"])
        self.network.assert_not_called()
        return code, folder, record


class RunLifecycle(RunFixture):
    def test_completed_run_preserves_evidence_and_removes_private_workspace(self):
        for platform_test in (True, False):
            with self.subTest(platform_test=platform_test):
                code, folder, record = self.run_preview(platform_test)
                self.assertEqual(code, 0)
                self.assertEqual(record["status"], "completed")
                self.assertEqual(record["errors"], [])
                self.assertFalse(record["posting_available"])
                self.assertEqual(record["transport_request_attempts"], 1)
                self.assertEqual(json.loads((folder / "started.json").read_text())["status"], "started")
                validation = json.loads((folder / "validation.json").read_text())
                self.assertEqual(validation["public_actions"], [])
                self.assertIsNone(validation["preview_comment"])
                for name in c.APPROVED:
                    self.assertEqual(rec.sha((folder / "input" / name).read_bytes()), c.APPROVED[name])
                hashes = json.loads((folder / "configuration-hashes.json").read_text())
                baseline.check_manifest(folder / "configuration", hashes["files"])
                self.assertEqual(record["configuration_sha256"], hashes["aggregate_sha256"])
        self.assertEqual(self.gate.close.call_count, 2)
        self.kill.assert_not_called()

    def test_invalid_output_remains_silent(self):
        self.raw = "not JSON"
        code, folder, record = self.run_preview()
        self.assertEqual((code, record["status"]), (1, "invalid_output"))
        validation = json.loads((folder / "validation.json").read_text())
        self.assertFalse(validation["valid"])
        self.assertEqual(validation["public_actions"], [])
        self.assertIsNone(validation["preview_comment"])
        self.gate.close.assert_called_once()

    def test_timeout_and_interruption_terminate_process_and_preserve_failure(self):
        for error, status in ((t.subprocess.TimeoutExpired("synthetic", 300), "failed"),
                              (KeyboardInterrupt(), "interrupted")):
            with self.subTest(status=status):
                self.process.poll.return_value = None
                self.process.communicate.side_effect = error
                code, folder, record = self.run_preview()
                self.assertEqual((code, record["status"]), (1, status))
                self.assertFalse((folder / "validation.json").exists())
                self.kill.assert_called_with(self.process.pid, t.signal.SIGKILL)
                self.process.wait.assert_called()
        self.assertEqual(self.gate.close.call_count, 2)

    def test_engine_and_transport_failures_are_recorded(self):
        for exit_code, errors, completion in ((1, [], {}), (0, ["Synthetic transport denial"], {}),
                                              (0, [], None)):
            with self.subTest(exit_code=exit_code, errors=errors, completion=completion):
                self.process.returncode = exit_code
                self.gate.errors = errors
                self.gate.completion = completion
                code, folder, record = self.run_preview()
                self.assertEqual((code, record["status"]), (1, "failed"))
                self.assertEqual(record["engine_exit_code"], exit_code)
                self.assertTrue(record["errors"])
                self.assertFalse((folder / "validation.json").exists())

    def test_unsupported_authentication_rejected_before_engine_launch(self):
        for auth in ({"auth_mode": "apikey"}, {**self.auth, "OPENAI_API_KEY": "synthetic"}):
            with self.subTest(auth=auth):
                (self.login / "auth.json").write_text(json.dumps(auth))
                code, folder, record = self.run_preview(platform_test=False)
                self.assertEqual((code, record["status"]), (1, "failed"))
                self.assertIn("API keys are not allowed", record["errors"][0])
                self.assertFalse((folder / "invocation.json").exists())
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()


class SyntheticRoutingFixtures(unittest.TestCase):
    def test_routing_contract_cases_match(self):
        fixture = c.ROOT / 'scripts/clarifier/tests/fixtures/routing.json'
        cases = json.loads(fixture.read_text())['cases']
        for case in cases:
            with self.subTest(raw=case['raw'][:100]):
                self.assertEqual(route.route(case['raw'], 'fixture', 'fixture-model'), case['result'])


class RejectedLifecycle(RunFixture):
    # Inherit fixture helpers without duplicating the original lifecycle tests.
    def test_configuration_rejected_before_engine_and_stays_publicly_silent(self):
        for index, alteration in enumerate(({'posting': True}, {'sandbox_repository_id': 1},
                                           {'input_limit_bytes': True}, {'tools': ['shell']})):
            with self.subTest(alteration=alteration):
                config = {**self.config, **alteration}
                (self.root / c.CONFIG_PATH).write_text(json.dumps(config))
                output = io.StringIO()
                with redirect_stdout(output):
                    code = p.run(True, root=self.root, id_factory=lambda: f'config-{index}')
                folder = Path(json.loads(output.getvalue())['folder'])
                record = json.loads((folder / 'record.json').read_text())
                self.assertEqual((code, record['status']), (1, 'failed'))
                self.assertEqual(record['public_actions'], [])
                self.assertFalse(record['posting_available'])
                self.assertFalse((folder / 'validation.json').exists())
        self.network.assert_not_called()
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()

    def test_skill_drift_is_rejected_without_engine_or_public_write(self):
        (self.root / c.SKILL_PATH).write_text('changed skill')
        code, folder, record = self.run_preview()
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.assertIn('Canonical skill hash mismatch', record['errors'])
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()

    def test_silent_decisions_and_failed_attribution_never_write_publicly(self):
        for decision in ('no_action', 'human_review'):
            self.raw = json.dumps({'decision': decision, 'rationale': 'Synthetic fixture.', 'clarification': None})
            code, folder, record = self.run_preview()
            routed = json.loads((folder / 'validation.json').read_text())
            self.assertEqual(code, 0)
            self.assertEqual(routed['public_actions'], [])
            self.assertIsNone(routed['preview_comment'])

    def test_gate_start_failure_is_closed_and_recorded(self):
        self.gate.start.side_effect = errors.TransportError('Synthetic gate start denial')
        code, folder, record = self.run_preview()
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.gate.close.assert_called_once()
        self.launch.assert_not_called()

    def test_credential_echoes_are_redacted_before_final_inventory(self):
        secret = self.auth['tokens']['access_token']
        original = self.complete_response
        def echo(prompt, timeout):
            original(prompt, timeout)
            folder = self.gate_factory.call_args.args[0]
            self.launch.call_args.kwargs['stderr'].write(('Bearer ' + secret).encode())
        self.process.communicate.side_effect = echo
        code, folder, record = self.run_preview(platform_test=False)
        self.assertEqual(code, 0)
        self.assertEqual((folder / 'stderr.txt').read_text(), 'Bearer [REDACTED]')
        self.assertEqual(record['redacted_artifacts'], [])
        for path in folder.rglob('*'):
            if path.is_file() and 'configuration' not in path.parts:
                self.assertNotIn(secret.encode(), path.read_bytes())


class CurrentEvidenceFlow(unittest.TestCase):
    def test_staged_prompt_contains_exact_approved_text(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            evidence = Path(tmp) / 'evidence'
            manifest = stage.stage(c.ROOT / c.CASE_PATH, evidence)
            prompt = req.build_prompt(evidence)
            envelope = json.loads(prompt.split('\n', 1)[1])
            self.assertEqual(set(envelope), {'files'})
            self.assertEqual(set(envelope['files']), set(c.APPROVED))
            for name, expected_hash in c.APPROVED.items():
                self.assertEqual(rec.sha(envelope['files'][name].encode()), expected_hash)
            self.assertEqual(manifest['staged_bytes'], sum((evidence / name).stat().st_size for name in c.APPROVED))


class EarlyFailures(RunFixture):
    def test_bad_source_is_rejected_without_engine_or_public_write(self):
        (self.root / c.CASE_PATH / 'body.md').write_text('changed')
        code, folder, record = self.run_preview()
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()

    def test_engine_version_drift_is_rejected_without_launch_or_public_write(self):
        self.version.return_value = Mock(stdout='codex-cli changed')
        code, folder, record = self.run_preview()
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()

    def test_missing_engine_is_recorded_without_launch_or_public_write(self):
        with patch.object(t.shutil, 'which', return_value=None):
            code, folder, record = self.run_preview()
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()

    def test_malformed_login_is_recorded_without_launch_or_public_write(self):
        (self.login / 'auth.json').write_text('{')
        code, folder, record = self.run_preview(False)
        self.assertEqual((code, record['status']), (1, 'failed'))
        self.launch.assert_not_called()
        self.gate_factory.assert_not_called()
