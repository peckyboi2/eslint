#!/usr/bin/env python3
"""Separate owner-only approval command, blocked before credentials. Serves C01."""
import json
import os
from pathlib import Path
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from clarifier.github import approval_io, workflow_io
from clarifier.shared import intake_constants as k
from clarifier.outputs.validation import parse_json
from clarifier.shared.errors import ClarifierError


def run() -> int:
    """Verify owner authority then reject absent live release; no public effects."""
    try:
        ctx=workflow_io.context(k.APPROVAL_WORKFLOW)
        approval_io.require_live_release()
        api=workflow_io.platform(ctx,True)
        return approval_io.post_approved(ctx,api,k.OUTPUT/'preview',parse_json(os.environ['EXACT_APPROVAL']))
    except ClarifierError as error:
        print(json.dumps(dict(status='blocked',error=str(error),public_actions=[])))
        return 1
    return 1


if __name__=='__main__':
    raise SystemExit(run())
