"""Guarded single-request inference; no public-write capability. Serves task 12 and R1.

The trusted host is not OS-jailed. HTTP credentials never enter recorded headers.
"""
from dataclasses import dataclass
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
from typing import Any

from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError, TransportError, ValidationError, guarded
from clarifier.inference.recording import PreviewConfig, Session, redact_text, save_json, sha, write_bytes, write_text
from clarifier.inference.request import make_config, prepare_request, record_request
from clarifier.inference.skill import LoadedSkill
from clarifier.inference.staging import StagedCase
from clarifier.outputs.validation import parse_json


@dataclass(frozen=True)
class Engine:
    """Pinned engine executable and private temporary login home."""
    binary: Path
    home: Path


@guarded(TransportError, "Malformed provider response")
def inspect_response(raw: bytes) -> tuple[dict[str, Any], str]:
    """Return one completed text response or raise TransportError before dispatch."""
    completed = []
    for line in raw.decode("utf-8").splitlines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        event = parse_json(line[6:])
        inspect_event(event)
        if event.get("type") == "response.completed":
            completed.append(event["response"])
    if len(completed) != 1 or completed[0].get("status") != "completed":
        raise TransportError("Expected one completed provider response")
    messages = [item for item in completed[0].get("output", []) if item.get("type") == "message"]
    if len(messages) != 1 or messages[0].get("role") != "assistant":
        raise TransportError("Expected one assistant result")
    contents = messages[0].get("content", [])
    if len(contents) != 1 or contents[0].get("type") != "output_text":
        raise TransportError("Expected one text result")
    if not isinstance(contents[0].get("text"), str):
        raise TransportError("Expected one text result")
    return completed[0], contents[0]["text"]


@guarded(TransportError, "Malformed provider event")
def inspect_event(event: dict[str, Any]) -> None:
    """Raise TransportError for tool, unsupported, incomplete or failed events."""
    kind = event.get("type", "")
    if kind in c.FAILED_EVENTS:
        raise TransportError("Provider returned a failed/incomplete response")
    if any(word in kind for word in c.FORBIDDEN_EVENTS):
        raise TransportError("Provider attempted a tool call")
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") not in c.ALLOWED_OUTPUT_ITEMS:
        raise TransportError("Provider returned an unsupported output item")
    for item in event.get("response", {}).get("output", []):
        if item.get("type") not in c.ALLOWED_OUTPUT_ITEMS:
            raise TransportError("Provider returned an unsupported output item")


class Gate(HTTPServer):
    """Loopback adapter that exposes one approved Responses exchange only."""

    @guarded(TransportError, "Cannot start bounded loopback transport")
    def __init__(self, folder: Path, skill: str, prompt: str,
                 config: PreviewConfig, platform_test: bool = False) -> None:
        """Bind the loopback gate or raise TransportError before inference."""
        super().__init__((c.LOOPBACK_HOST, c.LOOPBACK_PORT), Handler)
        self.folder, self.skill, self.prompt, self.config = folder, skill, prompt, config
        self.platform_test = platform_test
        self.attempts = 0
        self.errors: list[str] = []
        self.completion: dict[str, Any] | None = None
        self.secrets: list[str] = []
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.started = False

    @guarded(TransportError, "Cannot serve bounded loopback transport")
    def start(self) -> str:
        """Return the started loopback URL or raise TransportError."""
        self.thread.start()
        self.started = True
        return f"http://{c.LOOPBACK_HOST}:{self.server_port}"

    def close(self) -> None:
        """Close sockets and join the server thread, including unstarted gates."""
        if self.started:
            self.shutdown()
        self.server_close()
        if self.started:
            self.thread.join(timeout=c.THREAD_JOIN_SECONDS)


class Handler(BaseHTTPRequestHandler):
    """Trusted HTTP edge; untrusted request content cannot select an operation."""

    def log_message(self, *args: Any) -> None:
        """Suppress HTTP logging so headers cannot reach host logs."""

    def do_POST(self) -> None:
        """Dispatch one bounded request or return a silent transport denial."""
        gate = self.server
        gate.attempts += 1
        try:
            self.exchange()
        except ClarifierError as error:
            gate.errors.append(redact_text(str(error), gate.secrets))
            self.send_error(502, "Preview transport rejected request/response")

    @guarded(TransportError, "Preview transport rejected request/response")
    def exchange(self) -> None:
        """Perform the named request steps or raise a safe typed denial."""
        gate = self.server
        incoming = self.read_request()
        outgoing = prepare_request(incoming, gate.skill, gate.prompt, gate.config)
        record_request(gate.folder, incoming, gate.skill, outgoing)
        raw = synthetic_response() if gate.platform_test else self.fetch_provider(outgoing)
        self.record_response(raw)
        self.reply(raw)

    @guarded(TransportError, "Malformed or oversized native request")
    def read_request(self) -> dict[str, Any]:
        """Return a single bounded native request or raise TransportError."""
        if self.path != "/responses" or self.server.attempts != c.MAX_PROVIDER_REQUESTS:
            raise TransportError("Only one fixed Responses request is allowed")
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= c.MAX_REQUEST_BYTES or self.headers.get("Content-Encoding"):
            raise TransportError("Request encoding or size rejected")
        return parse_json(self.rfile.read(length))

    @guarded(TransportError, "Provider exchange failed")
    def fetch_provider(self, request: dict[str, Any]) -> bytes:
        """Return bounded HTTPS provider bytes or raise TransportError; never redirect."""
        headers = self.provider_headers()
        conn = http.client.HTTPSConnection(c.UPSTREAM_HOST, timeout=self.server.config["runtime_limit_seconds"])
        try:
            conn.request("POST", c.UPSTREAM_PATH, json.dumps(request).encode(), headers)
            response = conn.getresponse()
            raw = response.read(self.server.config["response_limit_bytes"] + 1)
            save_json(self.server.folder / c.PROVIDER_STATUS_FILE,
                      {"status": response.status, "host": c.UPSTREAM_HOST, "path": c.UPSTREAM_PATH})
            if response.status != 200:
                write_text(self.server.folder / c.PROVIDER_ERROR_FILE,
                           redact_text(raw.decode("utf-8", errors="replace"), self.server.secrets))
                raise TransportError(f"Provider HTTP {response.status}")
            return raw
        finally:
            conn.close()

    def provider_headers(self) -> dict[str, str]:
        """Return transient authentication headers or raise TransportError."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise TransportError("ChatGPT authentication unavailable")
        self.server.secrets.append(auth.removeprefix("Bearer "))
        headers = {"Content-Type": "application/json", "Authorization": auth,
                   "Accept": "text/event-stream", "User-Agent": self.server.config["cli_version"].replace(" ", "/")}
        for key in c.FORWARDED_HEADERS:
            if self.headers.get(key):
                headers[key] = self.headers[key]
        return headers

    def record_response(self, raw: bytes) -> None:
        """Preserve and inspect buffered bytes or raise TransportError/RecordingError."""
        write_text(self.server.folder / c.RESPONSE_FILE,
                   redact_text(raw.decode("utf-8", errors="replace"), self.server.secrets))
        if len(raw) > self.server.config["response_limit_bytes"]:
            raise TransportError("Provider response exceeds limit")
        completion, output = inspect_response(raw)
        write_text(self.server.folder / c.RAW_OUTPUT_FILE, redact_text(output, self.server.secrets))
        self.server.completion = completion

    def reply(self, raw: bytes) -> None:
        """Send only previously inspected provider bytes back to the CLI."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def credential_values(value: Any) -> list[str]:
    """Return authentication string values solely for in-memory redaction."""
    if isinstance(value, dict):
        return [text for item in value.values() for text in credential_values(item)]
    return [value] if isinstance(value, str) and value != "chatgpt" else []


@guarded(TransportError, "Cannot prepare existing ChatGPT authentication")
def copy_login(home: Path, session: Session) -> None:
    """Copy only existing ChatGPT credentials privately or raise TransportError."""
    source = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / c.AUTH_FILE
    data = source.read_bytes()
    try:
        auth = parse_json(data)
    except ValidationError:
        raise TransportError("Malformed existing ChatGPT authentication") from None
    if not isinstance(auth, dict) or auth.get("auth_mode") != "chatgpt" or auth.get("OPENAI_API_KEY"):
        raise TransportError("Existing ChatGPT authentication required; API keys are not allowed")
    session.secrets.extend(credential_values(auth))
    path = home / c.AUTH_FILE
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


@guarded(TransportError, "Cannot prepare pinned Codex engine")
def prepare_engine(session: Session) -> Engine:
    """Return a verified private engine or raise TransportError before launch."""
    found = shutil.which("codex")
    if not found:
        raise TransportError("Codex CLI unavailable")
    binary = Path(found).resolve()
    version = subprocess.run([str(binary), "--version"], capture_output=True, text=True,
                             check=True, timeout=session.config["runtime_limit_seconds"]).stdout.strip()
    session.record.update(engine_version=version, engine_binary_sha256=sha(binary.read_bytes()))
    if version != session.config["cli_version"]:
        raise TransportError("Codex CLI version differs from configured version")
    if session.temporary is None:
        raise TransportError("Missing private staging workspace")
    home = Path(session.temporary.name) / c.ENGINE_HOME_DIR
    home.mkdir(mode=0o700)
    if not session.platform_test:
        copy_login(home, session)
    return Engine(binary, home)


def invocation(engine: Engine, staged: StagedCase) -> tuple[list[str], dict[str, str]]:
    """Return the fixed CLI arguments and minimal environment without credentials."""
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "CODEX_HOME": str(engine.home),
           "TMPDIR": str(engine.home.parent), "LANG": "en_US.UTF-8"}
    argv = [str(engine.binary), "exec", "--strict-config", "--ephemeral", "--ignore-rules",
            "--skip-git-repo-check", "--json", "--color", "never", "-C", str(staged.workspace), "-"]
    return argv, env


@guarded(TransportError, "Cannot prepare restricted engine invocation")
def record_invocation(session: Session, engine: Engine, staged: StagedCase,
                      prompt: str, settings: str) -> tuple[list[str], dict[str, str]]:
    """Preserve deterministic CLI settings/arguments or raise a typed failure."""
    write_text(engine.home / c.NATIVE_CONFIG_FILE, settings)
    write_text(session.folder / c.ENGINE_CONFIG_FILE, settings)
    argv, env = invocation(engine, staged)
    save_json(session.folder / c.INVOCATION_FILE, {"argv": argv, "environment_keys": sorted(env),
              "stdin_sha256": sha(prompt.encode()), "engine_config_sha256": sha(settings.encode())})
    return argv, env


@guarded(TransportError, "Engine execution failed")
def execute_engine(workspace: Path, folder: Path, prompt: str,
                   argv: list[str], env: dict[str, str], timeout: int, secrets: list[str]) -> int:
    """Return the engine exit code, terminating its process group on interruption."""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                   cwd=workspace, env=env, start_new_session=True)
        try:
            process.communicate(prompt.encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TransportError("Inference runtime limit exceeded; process group terminated") from None
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            preserve_stream(folder / c.TRANSCRIPT_FILE, stdout, secrets)
            preserve_stream(folder / c.STDERR_FILE, stderr, secrets)
    return process.returncode


def preserve_stream(path: Path, stream: Any, secrets: list[str]) -> None:
    """Copy a private engine stream into redacted immutable evidence."""
    stream.seek(0)
    text = stream.read().decode("utf-8", errors="replace")
    write_text(path, redact_text(text, secrets))


@guarded(TransportError, "Cannot execute guarded preview")
def execute(session: Session, staged: StagedCase, loaded: LoadedSkill,
            prompt: str, engine: Engine) -> None:
    """Run the restricted engine once or raise a typed engine/transport failure."""
    session.gate = Gate(session.folder, loaded.text, prompt, session.config, session.platform_test)
    session.gate.secrets = session.secrets
    url = session.gate.start()
    settings = make_config(url, loaded.path, session.config, session.platform_test)
    argv, env = record_invocation(session, engine, staged, prompt, settings)
    session.record["engine_exit_code"] = execute_engine(
        staged.workspace, session.folder, prompt, argv, env,
        session.config["runtime_limit_seconds"], session.secrets)


@guarded(TransportError, "Cannot read bounded engine result")
def read_result(session: Session) -> str:
    """Return raw output only after successful engine/transport completion."""
    gate = session.gate
    if gate is None or gate.errors or session.record["engine_exit_code"] != 0 or gate.completion is None:
        raise TransportError("Engine/transport failed; inspect stderr, transcript and transport errors")
    return (session.folder / c.RAW_OUTPUT_FILE).read_text(encoding="utf-8")


def close(session: Session) -> None:
    """Close the gate and record bounded shutdown errors without losing evidence."""
    if session.gate:
        try:
            session.gate.close()
        except Exception:
            session.record["status"] = "failed"
            session.record["errors"].append("Preview transport shutdown failed")
        session.record["errors"].extend(redact_text(error, session.secrets) for error in session.gate.errors)
        session.record["transport_request_attempts"] = session.gate.attempts


def synthetic_response() -> bytes:
    """Infrastructure fixture; never historical inference or evaluation evidence."""
    text = json.dumps({"decision": "human_review", "rationale": "Synthetic transport fixture; no assessment performed.", "clarification": None})
    item = {"id": "msg_platform", "type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": text, "annotations": []}]}
    response = {"id": "resp_platform", "object": "response", "status": "completed", "model": "synthetic", "output": [item], "usage": None}
    events = [
        {"type": "response.created", "response": {**response, "status": "in_progress", "output": []}},
        {"type": "response.output_item.added", "output_index": 0, "item": {**item, "content": []}},
        {"type": "response.content_part.added", "item_id": item["id"], "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": "", "annotations": []}},
        {"type": "response.output_text.delta", "item_id": item["id"], "output_index": 0, "content_index": 0, "delta": text},
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {"type": "response.completed", "response": response},
    ]
    return "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events).encode()
