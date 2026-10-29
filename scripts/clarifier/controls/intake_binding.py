"""Bind live source, configuration, admission and artifacts. Serves B03–B04."""
from clarifier.controls import admission, ledger, policy as p
from clarifier.shared import intake_constants as k


def build(ctx, snapshot, configuration: dict) -> dict:
    """Return deterministic preview binding from trusted values; no model input authority."""
    key = admission.input_key(snapshot.hashes)
    return dict(version=k.VERSION, run_id=ctx.run_id, attempt=ctx.attempt, sha=ctx.sha,
                repository_id=p.REPOSITORY_ID, issue_id=snapshot.issue_id,
                source_issue=snapshot.number, source_sha256=snapshot.source_sha256,
                input_hashes=snapshot.hashes, input_key=key,
                event_key=admission.event_key(ctx,key), mode='preview',
                configuration=configuration, public_actions=[])


def validate(ctx, snapshot, configuration: dict, binding: dict, state: dict) -> None:
    """Raise AdmissionDenied for source/configuration/run/artifact/state mismatch."""
    expected = build(ctx,snapshot,configuration)
    if binding != expected:
        raise p.AdmissionDenied('Issue admission artifact identity mismatch')
    state = ledger.validate(state)
    if not state['enabled']:
        raise p.AdmissionDenied('Issue inference disabled')
    fields = ('run_id','input_key','event_key')
    if not any(all(row[key] == expected[key] for key in fields) for row in state['admissions']):
        raise p.AdmissionDenied('Issue persisted admission missing')
