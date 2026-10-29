"""Pure owner-reviewed dynamic output binding; no public I/O. Serves C01."""
from clarifier.controls import identity, policy as p
from clarifier.inference import live_snapshot, recording
from clarifier.outputs import output_handler, validation
from clarifier.shared import constants as c, intake_constants as k
from clarifier.shared.errors import StagingError, guarded


def preview_context(binding: dict) -> identity.Context:
    """Return original preview context or raise KeyError for malformed trusted binding."""
    return identity.Context(binding['run_id'],binding['attempt'],binding['sha'],p.TRIAGE_WORKFLOW,
                            'issues',binding['issue_id'],binding['source_issue'])


def expected_approval(binding: dict, raw: str, comment: str) -> dict:
    """Return exact review fields including the final attributed public bytes."""
    return dict(repository_id=p.REPOSITORY_ID,issue_id=binding['issue_id'],
                issue_number=binding['source_issue'],input_key=binding['input_key'],
                source_sha256=binding['source_sha256'],output_sha256=recording.sha(raw.encode()),
                comment_sha256=recording.sha(comment.encode()),
                configuration_sha256=binding['configuration']['aggregate_sha256'],
                preview_run_id=binding['run_id'],preview_attempt=binding['attempt'],code_sha=binding['sha'])


@guarded(p.PostingBlocked, 'Dynamic source or approval mismatch')
def plan(approval: dict, binding: dict, raw: str, issue: dict, state: dict):
    """Return exact dynamic CommentPlan or silent None; raise PostingBlocked on mismatch."""
    result=validation.parse_and_validate(raw)
    if result['decision'] != c.CLARIFY:
        return None
    output_handler.check_enabled(state)
    ctx=preview_context(binding)
    fresh=verified_source(ctx,issue)
    if fresh.hashes != binding['input_hashes'] or fresh.source_sha256 != binding['source_sha256']:
        raise p.PostingBlocked('Report changed since preview; exact approval invalid')
    marker=output_handler.attempt_marker(ctx,binding['event_key'],binding['configuration']['aggregate_sha256'])
    comment=output_handler.format_comment(result['clarification'],ctx,marker)
    if set(approval) != k.APPROVAL_KEYS or approval != expected_approval(binding,raw,comment):
        raise p.PostingBlocked('Exact human approval does not bind this output and target')
    return output_handler.CommentPlan(fresh.number,comment,binding['input_key'],binding['event_key'],
                                      binding['configuration']['aggregate_sha256'],marker)


def verified_source(ctx, issue: dict):
    """Return eligible source or raise PostingBlocked for any changed/unsupported report."""
    try:
        return live_snapshot.capture(ctx,issue,issue)
    except StagingError:
        raise p.PostingBlocked('Dynamic source changed or became ineligible') from None
