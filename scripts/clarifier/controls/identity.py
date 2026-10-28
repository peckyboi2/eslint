"""Pure reusable trigger/identity/ref gate for task 16; no credential access."""
from dataclasses import dataclass
import re
from typing import Any

from clarifier.shared.errors import guarded
from clarifier.controls import policy as p


@dataclass(frozen=True)
class Context:
    """Verified GitHub context; source is GitHub, never model output."""
    run_id: str
    attempt: int
    sha: str
    workflow: str


def require(value: bool, message: str) -> None:
    """Raise IdentityError unless a trusted-context invariant holds."""
    if not value:
        raise p.IdentityError(message)


@guarded(p.IdentityError, "Malformed trusted context")
def verify(data: dict[str, Any], workflow: str = p.TRIAGE_WORKFLOW) -> Context:
    """Return a bound context or raise IdentityError before any effect."""
    expected = {'event_name': 'workflow_dispatch', 'repository': p.REPOSITORY,
                'repository_id': str(p.REPOSITORY_ID), 'repository_owner': p.OWNER,
                'repository_owner_id': str(p.OWNER_ID), 'actor': p.OWNER,
                'actor_id': str(p.OWNER_ID), 'triggering_actor': p.OWNER,
                'ref': p.TRUSTED_REF, 'ref_type': 'branch'}
    require(all(data.get(k) == v for k, v in expected.items()), 'Trigger/identity/ref rejected')
    require(workflow in (p.TRIAGE_WORKFLOW, p.STOP_WORKFLOW), 'Unknown workflow')
    require(data.get('workflow_ref') == f'{p.REPOSITORY}/.github/workflows/{workflow}@{p.TRUSTED_REF}', 'Untrusted workflow ref')
    require(bool(re.fullmatch(p.GIT_SHA_PATTERN, str(data.get('sha', '')))), 'Missing trusted SHA')
    require(data.get('workflow_sha') == data['sha'], 'Workflow/code SHA mismatch')
    require(bool(re.fullmatch(p.RUN_PATTERN, str(data.get('run_id', '')))), 'Invalid run ID')
    require(bool(re.fullmatch(p.RUN_PATTERN, str(data.get('run_attempt', '')))), 'Invalid attempt')
    return Context(str(data['run_id']), int(data['run_attempt']), data['sha'], workflow)


@guarded(p.IdentityError, "Malformed live identity response")
def verify_live(context: Context, run: dict, repository: dict, initiator: dict) -> None:
    """Reject API/context disagreement, including original and rerun actor IDs."""
    require(repository.get('id') == p.REPOSITORY_ID and repository.get('full_name') == p.REPOSITORY, 'Live repository mismatch')
    require(repository.get('owner', {}).get('id') == p.OWNER_ID, 'Live owner mismatch')
    require(repository.get('default_branch') == 'main', 'Trusted default branch changed')
    require(run.get('id') == int(context.run_id) and run.get('run_attempt') == context.attempt, 'Live run mismatch')
    require(run.get('event') == 'workflow_dispatch' and run.get('head_branch') == 'main', 'Live trigger/ref mismatch')
    require(run.get('head_sha') == context.sha, 'Live SHA mismatch')
    for actor in (run.get('actor', {}), run.get('triggering_actor', {}), initiator):
        require(actor.get('id') == p.OWNER_ID and actor.get('login') == p.OWNER, 'Live actor mismatch')
    require(run.get('path') == f'.github/workflows/{context.workflow}', 'Live workflow mismatch')
