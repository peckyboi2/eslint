#!/usr/bin/env python3
"""Thin trusted platform orchestrator for task 19; defaults to preview."""
import argparse
import json

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clarifier.shared.errors import ClarifierError
from clarifier.controls import policy as p
from clarifier.github import workflow_io as io


def run(phase: str) -> int:
    """Run one gated deterministic phase; errors have no public output."""
    try:
        ctx = io.context()
        api = io.platform(ctx, phase in ('admit','post'))
        if phase == 'gate': return 0
        if phase == 'admit': io.prepare_admission(ctx,api); return 0
        binding = io.load_binding()
        if phase == 'infer': return io.infer(ctx,api,binding)
        if phase == 'post':
            from clarifier.outputs.posting import post_artifact
            return post_artifact(ctx,api,binding)
        raise p.PlatformError('Unknown trusted workflow phase')
    except ClarifierError as error:
        print(json.dumps(dict(status='blocked',error=str(error),public_actions=[])))
        return 1


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('gate','admit','infer','post'))
    raise SystemExit(run(parser.parse_args().phase))
