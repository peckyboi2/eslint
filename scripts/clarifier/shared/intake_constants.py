"""Named automatic-intake contracts and limits. Serves A03–C03."""
from pathlib import Path

VERSION = 'hosted-preview-v11'
BUG_PREFIX = 'Bug:'
EVENT_BYTES = 2097152
MAX_PENDING = 100
OUTPUT = Path('evals/automatic-workflow')
BINDING_FILE = 'admission.json'
SNAPSHOT_KEYS = ('id', 'number', 'title', 'body', 'state', 'locked', 'created_at', 'updated_at')
OPENING_ACTION = 'opened'
LIVE_FILES = ('title.txt', 'body.md', 'snapshot.json')
HOSTED_PROFILE = Path('scripts/clarifier/config/hosted.json')
APPROVAL_WORKFLOW = 'clarifier-approve.yml'
API_HOST, API_PATH = 'api.openai.com', '/v1/responses'
PROVIDER_KEY_ENV = 'CLARIFIER_PROVIDER_KEY'
READ_TOKEN_ENV = 'CLARIFIER_READ_TOKEN'
APPROVAL_KEYS = frozenset(('repository_id', 'issue_id', 'issue_number', 'input_key',
                          'source_sha256', 'output_sha256', 'comment_sha256',
                          'configuration_sha256', 'preview_run_id', 'preview_attempt', 'code_sha'))
