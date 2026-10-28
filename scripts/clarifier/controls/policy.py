"""Trusted sandbox identities and safety limits for tasks 16–28."""
from dataclasses import dataclass

from clarifier.shared.errors import ClarifierError


class IdentityError(ClarifierError):
    """Trusted trigger context is missing or inconsistent."""


class StateError(ClarifierError):
    """Ledger is absent, corrupt or conflicts with its expected parent."""


class AdmissionDenied(ClarifierError):
    """Admission is disabled, duplicated or exhausted."""


class PostingBlocked(ClarifierError):
    """A public comment cannot be proved safe."""


class PlatformError(ClarifierError):
    """A fixed platform operation failed; response text is never disclosed."""


class Conflict(StateError):
    """A non-forced branch update lost a race; reapply on fresh state."""


OWNER = 'peckyboi2'
OWNER_ID = 234542779
REPOSITORY = 'peckyboi2/eslint'
REPOSITORY_ID = 1435519573
TRUSTED_REF = 'refs/heads/main'
STATE_REF = 'heads/triage-state'
STATE_FILE = 'state.json'
TRIAGE_WORKFLOW = 'clarifier-triage.yml'
STOP_WORKFLOW = 'clarifier-stop.yml'
ROLLING_SECONDS = 86400
ROLLING_LIMIT = 10
LOCAL_EXCEPTION_LIMIT = 11
LOCAL_DEVELOPMENT_LIMIT = 21
LOCAL_CAMPAIGN_LIMIT = 21
LOCAL_EXTENSION_REASON = 'Owner approved local preview limits rolling=21 campaign=21; decision SHA-256 '
LOCAL_WORKFLOW = "local-development-preview"
SAFE_PLUGIN_SCOPE = "@typescript-eslint"
CAMPAIGN_LIMIT = 20
TRANSACTION_ATTEMPTS = 3
API_TIMEOUT = 30
API_LIMIT_BYTES = 2097152
ARTIFACT_DAYS = 30
JOB_MINUTES = 15
STOP_PASSES = 3
MAX_LEDGER_BYTES = 1048576
SHA_PATTERN = r'[a-f0-9]{64}'
GIT_SHA_PATTERN = r'[a-f0-9]{40}'
RUN_PATTERN = r'[1-9][0-9]*'
POLICY_VERSION = 'milestone-c-policy-v1'
CONFIG_VERSION = 'milestone-d-development-v3'


@dataclass(frozen=True)
class Target:
    """Owner-reviewed binding; None deliberately blocks live posting."""
    issue: int | None = None
    source_issue: int = 20373
    body_sha256: str = '52acebec10d033684d643df1c45c849b02967fa291806af3ee70f7e5ee1d0243'
    title_sha256: str = '8aacd3f7ce411c29e90e47cb1e6f9fab92581735ab2187f6dfaa28f5252fb8d3'


LIVE_TARGET = Target()
