"""Evaluator-side frozen campaign provenance checks. Serves tasks 51–62; never staged."""
import json
from pathlib import Path
from typing import TypedDict

from clarifier.inference import packages, recording, request
from clarifier.inference.staging import reject_unsafe_path
from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError, StagingError, guarded

CAMPAIGN_FOLDER = Path('evals/checks/gate-f-20261028')
MANIFEST_NAME = 'freeze.json'
ATTEMPT_STATUSES = ('completed', 'failed', 'interrupted', 'invalid_output')


class CampaignCase(TypedDict):
    """One predeclared attempt binding; contains no evaluator expectation."""
    issue: int
    run_id: str
    input_hashes: dict[str, str]
    attempt: int


class CampaignError(ClarifierError):
    """Frozen identities, isolation or attempt evidence cannot be established."""


def require(passed: bool, reason: str) -> None:
    """Raise CampaignError when an evaluator invariant fails."""
    if not passed:
        raise CampaignError(reason)


def digest_map(files: dict) -> str:
    """Return the canonical sorted-map identity used by the existing recorder."""
    return recording.sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())


@guarded(CampaignError, 'Cannot verify frozen content inventory')
def verify_files(root: Path, files: dict) -> None:
    """Raise CampaignError for unsafe, missing, symlinked or changed frozen files."""
    for name, expected in files.items():
        try:
            reject_unsafe_path(name)
        except StagingError:
            raise CampaignError('Unsafe frozen path') from None
        path = root / name
        require(not any(part.is_symlink() for part in (path, *path.parents)), 'Symlink in frozen path')
        require(recording.sha(path.read_bytes()) == expected, f'Frozen bytes changed: {name}')


@guarded(CampaignError, 'Cannot verify campaign freeze')
def verify_freeze(root: Path, manifest_sha256: str) -> dict:
    """Return one hash-bound manifest or raise CampaignError before inference/aggregation."""
    raw = (root / CAMPAIGN_FOLDER / MANIFEST_NAME).read_bytes()
    require(recording.sha(raw) == manifest_sha256, 'Campaign manifest changed')
    manifest = json.loads(raw)
    verify_files(root, manifest['files'])
    require(digest_map({str(p): recording.sha((root / p).read_bytes()) for p in c.CONFIG_PATHS})
            == manifest['configuration_sha256'], 'Runtime configuration changed')
    require([row['issue'] for row in manifest['cases']] == list(c.HISTORICAL_CASE_IDS), 'Case order changed')
    binary = Path(manifest['engine_binary'])
    require(recording.sha(binary.read_bytes()) == manifest['engine_binary_sha256'], 'Engine binary changed')
    for row in manifest['cases']:
        require(packages.load(row['issue'], root).hashes == row['input_hashes'], 'Package identity changed')
    return manifest


@guarded(CampaignError, 'Cannot verify retained attempt artifacts')
def read_attempt(root: Path, manifest: dict, case: dict) -> tuple[Path, dict]:
    """Return one declared immutable attempt; raise CampaignError on provenance loss."""
    folder = root / 'evals/runs' / case['run_id']
    inventory = json.loads((folder / c.ARTIFACT_HASHES_FILE).read_text())
    verify_files(folder, inventory)
    record = json.loads((folder / c.RECORD_FILE).read_text())
    require(record['run_id'] == case['run_id'] and record['source_issue'] == case['issue'], 'Run/case mismatch')
    require(record['configuration_sha256'] == manifest['configuration_sha256'], 'Mixed runtime configuration')
    require(record['input_hashes'] == case['input_hashes'], 'Run input mismatch')
    require(record['status'] in ATTEMPT_STATUSES, 'Unfinished attempt')
    require(record['public_actions'] == [] and record['posting_available'] is False, 'Public-write boundary failed')
    require(record['model_requested'] == manifest['model'], 'Requested model differs')
    return folder, record


@guarded(CampaignError, 'Malformed final preview route')
def verify_route(folder: Path, case: CampaignCase) -> dict:
    """Return one valid preview route or raise CampaignError for a silent/write violation."""
    route = json.loads((folder / c.VALIDATION_FILE).read_text())
    require(route['source_issue'] == case['issue'] and route['posting_target'] is None, 'Wrong route target')
    require(route['mode'] == 'preview' and route['public_actions'] == [], 'Route public-write boundary failed')
    result = route['validated_output']
    if result['decision'] != c.CLARIFY:
        require(route['preview_comment'] is None and result['clarification'] is None, 'Silent branch leaked comment')
    return result


@guarded(CampaignError, 'Malformed final isolation evidence')
def verify_isolation(root: Path, folder: Path, manifest: dict, case: CampaignCase, record: dict) -> None:
    """Raise CampaignError unless exact skill/case and fixed no-tool settings reached inference."""
    sent = json.loads((folder / c.REQUEST_FILE).read_text())
    loaded = json.loads((folder / c.LOADER_FILE).read_text())
    skill = (root / c.SKILL_PATH).read_text().strip()
    evidence = request.build_prompt(packages.load(case['issue'], root).source,
                                   c.EVIDENCE_ORDER + tuple(sorted(set(case['input_hashes']) - set(c.EVIDENCE_ORDER))))
    require(sent['input'] == [dict(role='developer', content=[dict(type='input_text', text=skill)]),
                             dict(role='user', content=[dict(type='input_text', text=evidence)])], 'Unexpected model context')
    require(sent == dict(model=manifest['model'], input=sent['input'], tools=[], tool_choice='none',
                         parallel_tool_calls=False, reasoning=dict(effort=manifest['reasoning_effort']),
                         store=False, stream=True), 'Model/tool/settings drift')
    require(loaded['loaded_content_sha256'] == recording.sha(skill.encode())
            and loaded['canonical_content_sha256'] == manifest['skill_sha256']
            and loaded['native_prompt_matched'] is True and loaded['implicit_host_context_forwarded'] is False,
            'Skill-load/isolation proof missing')
    require(record['engine_version'] == manifest['cli_version']
            and record['engine_binary_sha256'] == manifest['engine_binary_sha256']
            and record['model_returned'] == manifest['model'], 'Actual engine/model identity differs')
    require(record['inference_admitted'] is True and record['transport_request_attempts'] == 1
            and record['tool_calls'] == [] and not Path(record['model_workspace']).exists(), 'Execution isolation differs')


@guarded(CampaignError, 'Cannot inspect final attempt')
def inspect_case(root: Path, manifest: dict, case: CampaignCase) -> dict:
    """Return a final observation, preserving execution failures without borrowing earlier answers."""
    folder, record = read_attempt(root, manifest, case)
    result = None
    if record['status'] == 'completed':
        result = verify_route(folder, case)
        verify_isolation(root, folder, manifest, case, record)
    return dict(issue=case['issue'], run_id=case['run_id'], status=record['status'],
                actual_decision=result['decision'] if result else None, result=result,
                errors=record['errors'], input_hashes=record['input_hashes'],
                configuration_sha256=record['configuration_sha256'], public_actions=record['public_actions'],
                usage=record['usage'], cost=record['cost'], source=f'evals/golden/prepared-inputs/inputs/{case["issue"]}',
                run=f'evals/runs/{case["run_id"]}', campaign_id=manifest['campaign_id'])


@guarded(CampaignError, 'Cannot select final attempt')
def select_next(root: Path, manifest: dict, issue: int) -> CampaignCase:
    """Return the next declared attempt or raise CampaignError before a duplicate/out-of-order run."""
    selected = next((row for row in manifest['cases'] if not (root / 'evals/runs' / row['run_id']).exists()), None)
    require(selected is not None and selected['issue'] == issue, 'Duplicate or out-of-order campaign attempt')
    return selected


def record_boundary(root: Path, manifest: dict, case: dict, phase: str, manifest_hash: str) -> None:
    """Preserve a fresh evaluator manifest check outside all frozen/model instructions."""
    recording.save_json(root / CAMPAIGN_FOLDER / f'{case["issue"]}-{phase}.json',
                        dict(campaign_id=manifest['campaign_id'], issue=case['issue'], run_id=case['run_id'],
                             configuration_sha256=manifest['configuration_sha256'], freeze_sha256=manifest_hash,
                             phase=phase, verified_at=recording.utc(), files_verified=len(manifest['files'])))
