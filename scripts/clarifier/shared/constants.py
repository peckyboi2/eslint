"""Trusted paths, schemas and preview limits. Serves tasks 08–15, 29 and R1."""
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent.parent
SKILL_PATH = Path(".claude/skills/eslint-clarification/SKILL.md")
NATIVE_SKILL_PATH = Path(".agents/skills/eslint-clarification/SKILL.md")
CASE_PATH = Path("evals/golden/prepared-inputs/inputs/20373")
PREPARED_PATH = CASE_PATH.parent.parent
PACKAGE_MANIFEST = "manifest.json"
PACKAGE_HASHES = "SHA256-MANIFEST.json"
PACKAGE_MANIFEST_SHA256 = "29b9b0dcca6e4b2688afef630da97e6f46f2547bccf90fcee5dec65ad9ca2763"
PACKAGE_HASHES_SHA256 = "b3fc37075be7b82d02346f442bae83457b126f80908406419f16548f4b740594"
HISTORICAL_CASE_IDS = (20373, 20606, 19924, 19044, 21320, 19477, 21304, 19847, 19118, 19818)
CONFIG_PATH = Path("scripts/clarifier/config/config.json")
SCHEMA_PATH = Path("scripts/clarifier/config/decision.schema.json")
MODULE_PATHS = tuple(map(Path, (
    "shared/constants.py",
    "shared/errors.py",
    "preview.py",
    "c_preview.py",
    "workflow.py",
    "stop.py",
    "inference/staging.py",
    "inference/packages.py",
    "inference/skill.py",
    "inference/request.py",
    "inference/transport.py",
    "inference/recording.py",
    "inference/adversarial.py",
    "controls/policy.py",
    "controls/identity.py",
    "controls/ledger.py",
    "controls/admission.py",
    "controls/state_store.py",
    "controls/dry_state.py",
    "github/github_api.py",
    "github/workflow_io.py",
    "github/workflow_audit.py",
    "github/stop_io.py",
    "approve.py",
    "outputs/exact_approval.py",
    "outputs/dynamic_posting.py",
    "github/approval_io.py",
    "github/intake_audit.py",
    "shared/intake_constants.py",
    "controls/intake_identity.py",
    "controls/intake_binding.py",
    "github/issue_io.py",
    "github/intake_io.py",
    "inference/live_snapshot.py",
    "inference/pipeline.py",
    "inference/hosted_runtime.py",
    "inference/hosted_install.py",
    "inference/hosted_transport.py",
    "outputs/validation.py",
    "outputs/routing.py",
    "outputs/output_handler.py",
    "outputs/posting_intent.py",
    "outputs/posting.py",
    "outputs/release_gate.py",
    "outputs/campaign.py",
    "outputs/campaign_metrics.py",
)))
PACKAGE_PATHS = tuple(map(Path, (
    "__init__.py",
    "shared/__init__.py",
    "inference/__init__.py",
    "controls/__init__.py",
    "github/__init__.py",
    "outputs/__init__.py",
)))
SOURCE_PATHS = MODULE_PATHS + PACKAGE_PATHS
MODULE_NAMES = tuple(path.stem for path in MODULE_PATHS)
CONFIG_PATHS = (SKILL_PATH, CONFIG_PATH, SCHEMA_PATH,
                Path("scripts/clarifier/config/hosted.json"),
                *(Path("scripts/clarifier") / name for name in SOURCE_PATHS),
                Path("scripts/clarifier/tests/fixtures/attacks-v1.json"),
                Path(".github/workflows/clarifier-triage.yml"), Path(".github/workflows/clarifier-stop.yml"),
                Path(".github/workflows/clarifier-approve.yml"))
RETAINED_CONFIG_PATHS = (SKILL_PATH, CONFIG_PATH, SCHEMA_PATH, Path("scripts/clarifier/config/hosted.json"))
APPROVED = {
    "body.md": "52acebec10d033684d643df1c45c849b02967fa291806af3ee70f7e5ee1d0243",
    "title.txt": "8aacd3f7ce411c29e90e47cb1e6f9fab92581735ab2187f6dfaa28f5252fb8d3",
    "snapshot.json": "cb0a6bae09b182ec75254f2079ad7712ef4fa42f95e6456aa04a3eaadc0ee588",
}
EVIDENCE_ORDER = ("title.txt", "body.md", "snapshot.json")
EXCLUDED = ("Git metadata", "expected answers", "later discussion")
DECISION, RATIONALE, CLARIFICATION = "decision", "rationale", "clarification"
RESULT_KEYS = frozenset((DECISION, RATIONALE, CLARIFICATION))
CLARIFY, NO_ACTION, HUMAN_REVIEW = "clarify", "no_action", "human_review"
ALLOWED_DECISIONS = (CLARIFY, NO_ACTION, HUMAN_REVIEW)
MAX_INPUT_BYTES = 65536
MAX_OUTPUT_BYTES = 16384
MAX_RESPONSE_BYTES = 2097152
MAX_REQUEST_BYTES = 262144
MAX_RATIONALE_CHARS = 3000
MAX_CLARIFICATION_CHARS = 1500
MAX_COMMENT_CHARS = 2000
RUNTIME_SECONDS = 300
MAX_PROVIDER_REQUESTS = 1
MAX_SKILL_BYTES = MAX_INPUT_BYTES
SHA256_HEX_LENGTH = 64
RUN_SUFFIX_CHARS = 8
PRIVATE_TEMP_ROOT = str(Path(tempfile.gettempdir()).resolve())
WORKSPACE_DIR, EVIDENCE_DIR, INPUT_DIR = "workspace", "evidence", "input"
ENGINE_HOME_DIR, CONFIGURATION_DIR = "engine-home", "configuration"
STARTED_FILE, RECORD_FILE = "started.json", "record.json"
CONFIGURATION_HASHES_FILE = "configuration-hashes.json"
ARTIFACT_HASHES_FILE = "artifact-hashes.json"
MANIFEST_FILE, PROMPT_FILE = "input-manifest.json", "prompt.txt"
AUTH_FILE, ENGINE_CONFIG_FILE = "auth.json", "engine-config.toml"
NATIVE_CONFIG_FILE, INVOCATION_FILE = "config.toml", "invocation.json"
TRANSCRIPT_FILE, STDERR_FILE = "transcript.jsonl", "stderr.txt"
RAW_OUTPUT_FILE, RESPONSE_FILE = "raw-output.txt", "response.sse"
VALIDATION_FILE, NATIVE_PROBE_FILE = "validation.json", "native-load-probe.json"
LOADER_FILE, REQUEST_FILE = "loader.json", "request.json"
PROVIDER_STATUS_FILE, PROVIDER_ERROR_FILE = "provider-status.json", "provider-error.txt"
SOURCE_ISSUE = 20373
REPOSITORY = "peckyboi2/eslint"
REPOSITORY_ID = 1435519573
UPSTREAM_HOST = "chatgpt.com"
UPSTREAM_PATH = "/backend-api/codex/responses"
LOOPBACK_HOST, LOOPBACK_PORT = "127.0.0.1", 0
THREAD_JOIN_SECONDS = 2
UNKNOWN = "unknown"
FIXED_CONFIG = {
    "engine": "codex-cli", "cli_version": "codex-cli 0.154.0",
    "model": "gpt-6.1-sol", "reasoning_effort": "xhigh",
    "authentication": "existing ChatGPT login; no API key",
    "input_limit_bytes": MAX_INPUT_BYTES, "runtime_limit_seconds": RUNTIME_SECONDS,
    "output_limit_bytes": MAX_OUTPUT_BYTES, "response_limit_bytes": MAX_RESPONSE_BYTES,
    "comment_limit_characters": MAX_COMMENT_CHARS, "max_provider_requests": MAX_PROVIDER_REQUESTS,
    "mode": "preview", "tools": [], "source_issue": SOURCE_ISSUE,
    "sandbox_repository": REPOSITORY, "sandbox_repository_id": REPOSITORY_ID, "posting": False,
}
DISABLED_FEATURES = (
    "shell_tool", "shell_snapshot", "unified_exec", "apps", "plugins", "hooks",
    "memories", "multi_agent", "multi_agent_v2", "browser_use", "browser_use_external",
    "computer_use", "in_app_browser", "image_generation", "view_image", "code_mode",
    "code_mode_host", "skill_search", "skill_mcp_dependency_install", "workspace_dependencies",
    "goals", "sleep_tool", "unbounded_connection_retries", "enable_request_compression",
)
FORWARDED_HEADERS = ("ChatGPT-Account-Id", "OpenAI-Beta", "originator", "session_id")
ALLOWED_OUTPUT_ITEMS = ("message", "reasoning")
FORBIDDEN_EVENTS = ("function_call", "tool_call", "web_search", "computer_call", "shell_call")
FAILED_EVENTS = ("error", "response.failed", "response.incomplete")
HOST_ISOLATION = {
    "model_tools": [], "model_filesystem_interface": "none; approved text supplied inline",
    "model_network_interface": "none", "host_harness_os_jail": False,
    "host_network_firewall_tested": False,
    "trusted_harness": "Python recorder/gateway and pinned Codex binary can access host resources; model cannot call them",
    "gateway": "fixed HTTPS provider destination; no redirects; one request; response buffered before tool rejection",
    "credentials": "ChatGPT login only in temporary private engine home; none in model request; no posting/state credentials",
}
