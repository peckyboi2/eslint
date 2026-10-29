"""Validate new-issue identities without granting reporter authority. Serves B01."""
import re

from clarifier.controls import identity, policy as p
from clarifier.shared.errors import guarded


@guarded(p.IdentityError, 'Malformed issue-event context')
def verify(data: dict, event: dict) -> identity.Context:
    """Return first-attempt issue context or raise IdentityError before effects."""
    expected = dict(event_name='issues', repository=p.REPOSITORY,
                    repository_id=str(p.REPOSITORY_ID), repository_owner=p.OWNER,
                    repository_owner_id=str(p.OWNER_ID), ref=p.TRUSTED_REF,
                    ref_type='branch', run_attempt='1')
    identity.require(all(data.get(k) == v for k, v in expected.items()), 'Issue trigger/ref rejected')
    path = f'{p.REPOSITORY}/.github/workflows/{p.TRIAGE_WORKFLOW}@{p.TRUSTED_REF}'
    identity.require(data.get('workflow_ref') == path, 'Untrusted issue workflow')
    identity.require(bool(re.fullmatch(p.GIT_SHA_PATTERN, data.get('sha', ''))), 'Invalid code SHA')
    identity.require(data.get('workflow_sha') == data['sha'], 'Issue workflow/code mismatch')
    identity.require(bool(re.fullmatch(p.RUN_PATTERN, data.get('run_id', ''))), 'Invalid issue run')
    identity.require(event.get('action') == 'opened', 'Only issue opening is accepted')
    repo, issue = event['repository'], event['issue']
    identity.require(repo['id'] == p.REPOSITORY_ID and repo['full_name'] == p.REPOSITORY, 'Event repository mismatch')
    identity.require(repo['owner']['id'] == p.OWNER_ID and repo['owner']['login'] == p.OWNER, 'Event owner mismatch')
    identity.require(repo['default_branch'] == 'main', 'Default branch changed')
    identity.require(type(issue['id']) is int and issue['id'] > 0, 'Invalid issue ID')
    identity.require(type(issue['number']) is int and issue['number'] > 0, 'Invalid issue number')
    sender = event['sender']
    identity.require(str(sender['id']) == data.get('actor_id') and sender['login'] == data.get('actor'), 'Sender/actor mismatch')
    identity.require(data.get('triggering_actor') == sender['login'], 'Issue rerun actor rejected')
    return identity.Context(data['run_id'], 1, data['sha'], p.TRIAGE_WORKFLOW,
                            'issues', issue['id'], issue['number'], sender['id'], sender['login'])


@guarded(p.IdentityError, 'Malformed live issue-run identity')
def verify_live(context: identity.Context, run: dict, repository: dict, initiator: dict) -> None:
    """Raise IdentityError on repository/run/ref disagreement; reporters need no owner role."""
    identity.require(repository['id'] == p.REPOSITORY_ID and repository['full_name'] == p.REPOSITORY, 'Live repository mismatch')
    identity.require(repository['owner']['id'] == p.OWNER_ID and repository['owner']['login'] == p.OWNER, 'Live owner mismatch')
    identity.require(repository['default_branch'] == 'main', 'Live default branch changed')
    identity.require(run['id'] == int(context.run_id) and run['run_attempt'] == 1, 'Live issue attempt mismatch')
    identity.require(run['event'] == 'issues' and run['head_branch'] == 'main', 'Live issue trigger mismatch')
    identity.require(run['head_sha'] == context.sha and run['path'] == f'.github/workflows/{p.TRIAGE_WORKFLOW}', 'Live issue code mismatch')
    original, trigger = run['actor'], run['triggering_actor']
    for actor in (original, trigger):
        identity.require(actor['id'] == context.actor_id and actor['login'] == context.actor_login, 'Live issue actor mismatch')
