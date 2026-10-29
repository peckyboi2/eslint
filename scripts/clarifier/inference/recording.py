"""Append-only configuration and run evidence. Serves tasks 14, 29 and R1."""
from dataclasses import dataclass, field
from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Any, Callable, TYPE_CHECKING, TypedDict
import uuid

from clarifier.shared import constants as c
from clarifier.shared.errors import (ClarifierError, ConfigurationError, InterruptedRun,
                    RecordingError, ValidationError, guarded)
from clarifier.outputs.routing import PreviewRoute, rejected
from clarifier.outputs.validation import parse_json

if TYPE_CHECKING:
    from clarifier.inference.transport import Gate


class PreviewConfig(TypedDict):
    """The bounded engine settings; fixed values are checked before staging."""
    version: str
    engine: str
    input_hashes: dict[str, str] | str
    cli_version: str
    model: str
    reasoning_effort: str
    authentication: str
    input_limit_bytes: int
    runtime_limit_seconds: int
    output_limit_bytes: int
    response_limit_bytes: int
    comment_limit_characters: int
    max_provider_requests: int
    mode: str
    tools: list
    source_issue: int
    sandbox_repository: str
    sandbox_repository_id: int
    posting: bool
    skill_sha256: str


class RunRecord(TypedDict, total=False):
    """Recorded facts; missing engine facts remain explicitly unknown."""
    run_id: str
    started_at: str
    finished_at: str
    status: str
    trigger: str
    kind: str
    verification_type: str
    source_issue: int
    model_requested: str
    engine: str
    usage: Any
    cost: Any
    errors: list[str]
    posting_available: bool
    public_actions: list
    backend_revision_pinned: bool
    configuration_sha256: str
    configuration_version: str
    engine_version: str
    engine_binary_sha256: str
    engine_exit_code: int
    model_returned: str
    transport_request_attempts: int
    skill_loaded_path: str
    skill_sha256: str
    model_workspace: str
    host_isolation: dict
    tool_calls: list
    tool_calls_evidence: str
    redacted_artifacts: list[str]
    historical_cutoff: dict
    inference_admitted: bool


@dataclass
class Session:
    """Trusted runtime resources; temporary credentials never enter RunRecord."""
    root: Path
    folder: Path
    record: RunRecord
    platform_test: bool
    clock: Callable[[], str]
    _config: PreviewConfig | None = None
    temporary: TemporaryDirectory | None = None
    gate: "Gate | None" = None
    secrets: list[str] = field(default_factory=list, repr=False)

    @property
    def config(self) -> PreviewConfig:
        """Return verified configuration or raise ConfigurationError before use."""
        if self._config is None:
            raise ConfigurationError("Preview configuration has not been verified")
        return self._config

    @config.setter
    def config(self, config: PreviewConfig) -> None:
        """Store already validated configuration for subsequent named steps."""
        self._config = config


def sha(data: bytes) -> str:
    """Return the SHA-256 content digest."""
    return hashlib.sha256(data).hexdigest()


def utc() -> str:
    """Return the current UTC timestamp for an injectable run clock."""
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    """Return a unique timestamped run identity."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:c.RUN_SUFFIX_CHARS]


def redact_text(text: str, secrets: Sequence[str] = ()) -> str:
    """Return text with known credentials and bearer values removed."""
    for secret in sorted(filter(None, secrets), key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    return re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", text)


def redact(value: Any) -> Any:
    """Return JSON data with credential fields and bearer values removed."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in {
            "authorization", "access_token", "refresh_token", "id_token", "openai_api_key", "password",
            "gh_token", "github_token", "token", "codex_api_key", "clarifier_provider_key", "client_secret", "cookie"
        } else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return redact_text(value) if isinstance(value, str) else value


@guarded(RecordingError, "Cannot create immutable evidence file")
def write_bytes(path: Path, data: bytes) -> None:
    """Create an evidence file exclusively or raise RecordingError."""
    with path.open("xb") as stream:
        stream.write(data)


@guarded(RecordingError, "Cannot encode immutable text evidence")
def write_text(path: Path, text: str) -> None:
    """Create UTF-8 evidence exclusively or raise RecordingError."""
    write_bytes(path, text.encode("utf-8"))


@guarded(RecordingError, "Cannot encode immutable JSON evidence")
def save_json(path: Path, value: Any, secrets: Sequence[str] = ()) -> None:
    """Create credential-redacted JSON exclusively or raise RecordingError."""
    text = json.dumps(redact(value), ensure_ascii=False, indent=2) + "\n"
    write_text(path, redact_text(text, secrets))


@guarded(RecordingError, "Cannot identify configuration")
def record_configuration(folder: Path, root: Path = c.ROOT,
                         paths: tuple[Path, ...] = c.CONFIG_PATHS) -> str:
    """Retain settings/instructions and source hashes; return their aggregate identity."""
    retained, sources = {}, {}
    for name in paths:
        data = (root / name).read_bytes()
        if name in c.RETAINED_CONFIG_PATHS:
            preserve_configuration_file(folder, name, data)
            retained[name.as_posix()] = sha(data)
        else:
            sources[name.as_posix()] = sha(data)
    hashes = {**retained, **sources}
    aggregate = sha(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode())
    save_json(folder / c.CONFIGURATION_HASHES_FILE,
              {"files": retained, "source_hashes": sources, "aggregate_sha256": aggregate})
    return aggregate


def preserve_configuration_file(folder: Path, name: Path, data: bytes) -> None:
    """Create one exact instruction/settings artifact or raise RecordingError."""
    target = folder / c.CONFIGURATION_DIR / name
    target.parent.mkdir(parents=True, exist_ok=True)
    write_bytes(target, data)


@guarded(RecordingError, "Cannot start immutable run record")
def start_run(platform_test: bool, root: Path = c.ROOT,
              clock: Callable[[], str] = utc, id_factory: Callable[[], str] = new_run_id,
              *, source_issue: int = c.SOURCE_ISSUE) -> Session:
    """Return a new run session or raise RecordingError before any engine call."""
    run_id = id_factory()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id) or run_id in (".", ".."):
        raise RecordingError("Unsafe run identity")
    folder = root / "evals" / ("platform-tests" if platform_test else "runs") / run_id
    folder.mkdir(parents=True, exist_ok=False)
    record = RunRecord(run_id=run_id, started_at=clock(), status="started",
                       trigger="manual Milestone B authorised development preview",
                       kind="synthetic platform test" if platform_test else "actual Codex ChatGPT dry run",
                       verification_type="synthetic infrastructure" if platform_test else "model dry run",
                       source_issue=source_issue, model_requested=c.UNKNOWN, engine=c.UNKNOWN,
                       input_hashes=c.UNKNOWN, skill_sha256=c.UNKNOWN, engine_version=c.UNKNOWN,
                       model_returned=c.UNKNOWN,
                       usage=c.UNKNOWN, cost=c.UNKNOWN, errors=[], posting_available=False,
                       public_actions=[], backend_revision_pinned=False)
    save_json(folder / c.STARTED_FILE, record)
    return Session(root, folder, record, platform_test, clock)


def validate_configuration(config: Any) -> PreviewConfig:
    """Return fixed preview settings or raise ConfigurationError before admission."""
    if not isinstance(config, dict) or set(config) != set(c.FIXED_CONFIG) | {"version", "skill_sha256"}:
        raise ConfigurationError("Unexpected or missing configuration fields")
    for key, expected in c.FIXED_CONFIG.items():
        if type(config[key]) is not type(expected) or config[key] != expected:
            raise ConfigurationError("Configuration differs from bounded preview policy")
    if not isinstance(config["version"], str) or not config["version"].strip():
        raise ConfigurationError("Configuration version is missing")
    if not isinstance(config["skill_sha256"], str) or not re.fullmatch(rf"[a-f0-9]{{{c.SHA256_HEX_LENGTH}}}", config["skill_sha256"]):
        raise ConfigurationError("Canonical skill hash is missing or invalid")
    return config


@guarded(ConfigurationError, "Cannot load preview configuration")
def configure(session: Session) -> None:
    """Preserve and load configuration or raise ConfigurationError."""
    session.record["configuration_sha256"] = record_configuration(session.folder, session.root)
    session.config = load_configuration(session.folder / c.CONFIGURATION_DIR / c.CONFIG_PATH)
    session.record.update(configuration_version=session.config["version"],
                          model_requested=session.config["model"], engine=session.config["engine"])


def mark_local_attempt(session: Session) -> None:
    """Identify an unadmitted local attempt without implying a model execution."""
    session.record.update(trigger="Darren-authorised local development preview",
                          kind="local preview attempt", verification_type="local pre-inference checks",
                          transport_request_attempts=0, inference_admitted=False)


@guarded(ConfigurationError, "Cannot read preview configuration")
def load_configuration(path: Path) -> PreviewConfig:
    """Return strict preview configuration or raise ConfigurationError."""
    try:
        config = parse_json(path.read_text(encoding="utf-8"))
    except ValidationError:
        raise ConfigurationError("Malformed preview configuration JSON") from None
    return validate_configuration(config)


def record_result(session: Session, route: PreviewRoute) -> None:
    """Save a validated route or raise RecordingError on evidence failure."""
    if session.gate is None or session.gate.completion is None:
        raise RecordingError("Missing completed transport evidence")
    completion = session.gate.completion
    save_json(session.folder / c.VALIDATION_FILE, route)
    session.record.update(status="completed", usage=completion.get("usage") or c.UNKNOWN,
                          model_returned=completion.get("model") or c.UNKNOWN,
                          tool_calls=[], tool_calls_evidence="guarded response.sse contains no tool items")


def fail(session: Session, error: ClarifierError) -> None:
    """Record a typed failure, keeping every rejected branch publicly silent."""
    status = "interrupted" if isinstance(error, InterruptedRun) else "failed"
    if isinstance(error, ValidationError):
        status = "invalid_output"
        save_json(session.folder / c.VALIDATION_FILE, rejected(error, source_issue=session.record['source_issue'],
                  trusted_live=session.record.get('trigger')=='issues:opened'))
    session.record.update(status=status)
    session.record["errors"].append(redact_text(str(error), session.secrets))


@guarded(RecordingError, "Cannot redact runtime evidence")
def redact_artifacts(session: Session) -> None:
    """Remove credential values from current-run text before its final inventory."""
    changed = []
    for path in session.folder.iterdir():
        if path.is_file() and path.suffix in (".txt", ".json", ".jsonl", ".sse", ".toml"):
            text = path.read_text(encoding="utf-8")
            safe = redact_text(text, session.secrets)
            if safe != text:
                path.write_text(safe, encoding="utf-8")
                changed.append(path.name)
    session.record["redacted_artifacts"] = changed


@guarded(RecordingError, "Cannot finish run evidence")
def finish(session: Session) -> None:
    """Finalize and hash a fresh run record or raise RecordingError."""
    redact_artifacts(session)
    session.record["finished_at"] = session.clock()
    save_json(session.folder / c.RECORD_FILE, session.record, session.secrets)
    inventory = {path.relative_to(session.folder).as_posix(): sha(path.read_bytes())
                 for path in sorted(session.folder.rglob("*")) if path.is_file()}
    save_json(session.folder / c.ARTIFACT_HASHES_FILE, inventory)


def report(session: Session) -> int:
    """Print the unchanged CLI summary shape and return its completion exit code."""
    print(json.dumps({"folder": str(session.folder), "status": session.record["status"],
                      "errors": session.record["errors"]}))
    return 0 if session.record["status"] == "completed" else 1
