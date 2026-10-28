"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import constants as c
import errors
import recording as rec
import transport as t


class ProviderResponses(unittest.TestCase):
    def test_response_tools_blocked_before_dispatch(self):
        for kind in ("function_call", "custom_tool_call", "web_search_call", "computer_call", "local_shell_call"):
            raw = ('data: ' + json.dumps({"type": "response.output_item.added", "item": {"type": kind}}) + '\n\n').encode()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                t.inspect_response(raw + t.synthetic_response())
        with self.assertRaises(ValueError):
            t.inspect_response(b'data: {"type":"response.function_call_arguments.delta"}\n\n' + t.synthetic_response())
        for raw in (b'', t.synthetic_response() * 2, b'data: {"type":"response.failed"}\n\n'):
            with self.assertRaises(ValueError):
                t.inspect_response(raw)

    def test_synthetic_fixture_is_labelled_and_has_no_usage_claim(self):
        completed, raw = t.inspect_response(t.synthetic_response())
        self.assertEqual(completed["model"], "synthetic")
        self.assertIsNone(completed["usage"])
        self.assertIn("Synthetic transport fixture", raw)


class GuardedHTTP(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        self.gate = SimpleNamespace(folder=self.folder, config=self.config, attempts=0, errors=[],
                                    completion=None, platform_test=True, skill='skill', prompt='prompt', secrets=[])
        self.handler = object.__new__(t.Handler)
        self.handler.server = self.gate
        self.handler.path = '/responses'
        self.incoming = {'model': self.config['model'], 'instructions': 'skill',
                         'input': [{'role': 'user', 'content': [{'text': 'prompt'}]}]}
        self.handler.send_error = Mock()
        self.handler.reply = Mock()
        self.network = self.enterContext(patch.object(t.http.client, 'HTTPSConnection'))

    def invoke(self, payload=None, headers=None):
        payload = json.dumps(self.incoming).encode() if payload is None else payload
        self.handler.headers = {'Content-Length': str(len(payload)), **(headers or {})}
        self.handler.rfile = io.BytesIO(payload)
        self.handler.do_POST()

    def assert_no_dispatch(self):
        self.network.assert_not_called()
        self.handler.reply.assert_not_called()
        self.assertIsNone(self.gate.completion)
        self.assertTrue(self.gate.errors)
        self.assertFalse((self.folder / 'raw-output.txt').exists())

    def test_path_rejection_is_silent_and_cannot_reach_provider(self):
        self.handler.path = '/issues/20373/comments'
        self.invoke()
        self.assert_no_dispatch()

    def test_duplicate_request_is_silent_before_provider_dispatch(self):
        self.gate.attempts = 1
        self.invoke()
        self.assert_no_dispatch()

    def test_oversize_and_encoded_requests_are_rejected_without_dispatch(self):
        for headers in ({'Content-Length': str(c.MAX_REQUEST_BYTES + 1)}, {'Content-Encoding': 'gzip'}):
            with self.subTest(headers=headers):
                self.gate.attempts = 0
                self.invoke(headers=headers)
                self.assert_no_dispatch()

    def test_malformed_request_is_rejected_without_dispatch(self):
        self.invoke(b'null')
        self.assert_no_dispatch()

    def test_skill_mismatch_is_rejected_without_dispatch(self):
        self.incoming['instructions'] = 'altered skill'
        self.invoke()
        self.assert_no_dispatch()

    def test_forbidden_response_is_buffered_without_cli_dispatch(self):
        self.gate.platform_test = False
        poison = b'data: {"type":"response.output_item.added","item":{"type":"function_call"}}\n\n'
        self.handler.fetch_provider = Mock(return_value=poison + t.synthetic_response())
        self.invoke()
        self.assert_no_dispatch()
        self.assertTrue((self.folder / 'response.sse').exists())

    def test_synthetic_response_is_local_and_labelled(self):
        self.invoke()
        self.network.assert_not_called()
        self.handler.reply.assert_called_once_with(t.synthetic_response())
        self.assertEqual(self.gate.completion['model'], 'synthetic')
        request = json.loads((self.folder / 'request.json').read_text())
        self.assertEqual(request['tools'], [])
        self.assertEqual(request['tool_choice'], 'none')

    def test_provider_headers_stay_transient_and_target_is_fixed(self):
        self.handler.headers = {'Authorization': 'Bearer transient-secret'}
        conn = self.network.return_value
        response = conn.getresponse.return_value
        response.status = 200
        response.read.return_value = t.synthetic_response()
        self.assertEqual(self.handler.fetch_provider({}), t.synthetic_response())
        self.network.assert_called_once_with(c.UPSTREAM_HOST, timeout=c.RUNTIME_SECONDS)
        args = conn.request.call_args.args
        self.assertEqual(args[:2], ('POST', c.UPSTREAM_PATH))
        self.assertEqual(args[3]['Authorization'], 'Bearer transient-secret')
        conn.close.assert_called_once()
        self.assertNotIn('transient-secret', ''.join(path.read_text() for path in self.folder.iterdir()))

    def test_provider_error_redacts_credentials_before_recording(self):
        self.handler.headers = {'Authorization': 'Bearer transient-secret'}
        conn = self.network.return_value
        response = conn.getresponse.return_value
        response.status = 401
        response.read.return_value = b'echo transient-secret'
        with self.assertRaises(errors.TransportError):
            self.handler.fetch_provider({})
        self.assertEqual((self.folder / 'provider-error.txt').read_text(), 'echo [REDACTED]')
        self.handler.reply.assert_not_called()
        conn.close.assert_called_once()

    def test_oversize_response_cannot_dispatch(self):
        self.gate.config = {**self.config, 'response_limit_bytes': 1}
        self.invoke()
        self.assert_no_dispatch()


class MalformedResponses(unittest.TestCase):
    def test_structural_and_utf8_errors_raise_typed_errors(self):
        for raw in (b'\xff', b'data: null\n\n', b'data: {"type":"response.completed","response":null}\n\n'):
            with self.subTest(raw=raw), self.assertRaises(errors.ClarifierError):
                t.inspect_response(raw)


class GateLifecycle(unittest.TestCase):
    def test_unstarted_gate_closes_without_waiting_for_server_loop(self):
        with patch.object(t.HTTPServer, '__init__', return_value=None), patch.object(t.threading, 'Thread'):
            gate = t.Gate(Path('/unused'), 'skill', 'prompt', {})
            with patch.object(gate, 'shutdown') as shutdown, patch.object(gate, 'server_close') as close:
                gate.close()
                shutdown.assert_not_called()
                close.assert_called_once()
                gate.thread.join.assert_not_called()

    def test_started_gate_serves_only_loopback_and_closes_thread(self):
        with patch.object(t.HTTPServer, '__init__', return_value=None), patch.object(t.threading, 'Thread'):
            gate = t.Gate(Path('/unused'), 'skill', 'prompt', {})
            gate.server_port = 12345
            self.assertEqual(gate.start(), 'http://127.0.0.1:12345')
            with patch.object(gate, 'shutdown') as shutdown, patch.object(gate, 'server_close') as close:
                gate.close()
                shutdown.assert_called_once()
                close.assert_called_once()
                gate.thread.join.assert_called_once_with(timeout=c.THREAD_JOIN_SECONDS)

    def test_shutdown_error_is_recorded_and_remains_publicly_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = rec.start_run(True, Path(tmp), id_factory=lambda: 'shutdown')
            session.gate = Mock(errors=[], attempts=1)
            session.gate.close.side_effect = OSError('Bearer private-value')
            t.close(session)
            self.assertEqual(session.record['status'], 'failed')
            self.assertEqual(session.record['public_actions'], [])
            self.assertFalse(session.record['posting_available'])
            self.assertEqual(session.record['errors'], ['Preview transport shutdown failed'])
