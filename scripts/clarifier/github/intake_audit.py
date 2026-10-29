"""Redacted internal phase receipts, including silent skips. Serves C02."""
import os

from clarifier.inference import recording
from clarifier.github import workflow_io
from clarifier.shared import constants as c, intake_constants as k


def write_phase(phase: str, ctx=None, snapshot=None, error=None) -> None:
    """Save one bounded internal receipt or raise RecordingError; never save raw event text."""
    k.OUTPUT.mkdir(parents=True,exist_ok=True)
    row=dict(trigger='issues:opened',phase=phase,status='blocked' if error else 'passed',
             run_id=ctx.run_id if ctx else os.environ.get('GITHUB_RUN_ID',c.UNKNOWN),
             attempt=ctx.attempt if ctx else c.UNKNOWN,code_sha=ctx.sha if ctx else c.UNKNOWN,
             issue_id=snapshot.issue_id if snapshot else c.UNKNOWN,
             source_issue=snapshot.number if snapshot else c.UNKNOWN,
             input_hashes=snapshot.hashes if snapshot else c.UNKNOWN,
             configuration=workflow_io.fingerprint(),
             source_sha256=snapshot.source_sha256 if snapshot else c.UNKNOWN,
             error=str(error) if error else None,model_requested=c.FIXED_CONFIG['model'],usage=c.UNKNOWN,
             cost=c.UNKNOWN,public_actions=[],at=recording.utc(),
             provider_status='No provider dispatch in gate/admit; infer record is authoritative')
    recording.save_json(k.OUTPUT/(phase+'-audit.json'),row)
