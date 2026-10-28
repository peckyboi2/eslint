#!/usr/bin/env python3
"""Independent emergency-stop orchestrator for task 22, without triage dependencies."""
import argparse
import json
import time

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clarifier.shared.errors import ClarifierError, guarded
from clarifier.controls import policy as p
from clarifier.inference.recording import save_json
from clarifier.controls.state_store import StateStore
from clarifier.github import stop_io as io
from clarifier.github import workflow_io


def execute(api, ctx, store, at: int, reason: str) -> dict:
    """Disable future work, cancel active/pending work and inspect possible writes."""
    report=dict(ledger_disabled=False,workflow_disabled=False,cancellation_requests=[],
                unresolved_runs=['inspection incomplete'],inflight_intents=[],errors=[],public_actions=[])
    io.disable_admission(store,at,reason,report)
    io.disable_triage(api,ctx,report)
    io.cancel_runs(api,ctx,report)
    io.inspect_writes(api,ctx,store,report)
    return report


@guarded(p.PlatformError,'Stop platform response malformed; inspect Actions and ledger manually')
def run(phase: str) -> int:
    """Run independently gated stop; retain failures without claiming termination."""
    ctx=workflow_io.context(p.STOP_WORKFLOW)
    api=workflow_io.platform(ctx,phase=='execute')
    if phase=='gate': return 0
    report=execute(api,ctx,StateStore(api,ctx),int(time.time()),'Owner manual emergency stop')
    workflow_io.OUTPUT.mkdir(parents=True,exist_ok=True)
    save_json(workflow_io.OUTPUT/'stop.json',report)
    return int(bool(report['errors'] or report['unresolved_runs'] or not report['ledger_disabled'] or not report['workflow_disabled']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('gate','execute'))
    try: code=run(parser.parse_args().phase)
    except ClarifierError as error: print(json.dumps(dict(status='blocked',error=str(error))));code=1
    raise SystemExit(code)
