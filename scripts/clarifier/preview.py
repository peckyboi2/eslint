#!/usr/bin/env python3
"""Milestone B preview only. Serves tasks 09–15 and R1; no posting capability."""
import argparse
from pathlib import Path
from typing import Callable

import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError
from clarifier.inference import recording
from clarifier.inference import pipeline
from clarifier.inference import request
from clarifier.inference import staging
from clarifier.inference import transport


def run(platform_test: bool = False, *, root: Path = c.ROOT,
        clock: Callable[[], str] = recording.utc,
        id_factory: Callable[[], str] = recording.new_run_id) -> int:
    """Run named preview steps and return the recorded CLI exit code."""
    session = recording.start_run(platform_test, root, clock, id_factory)
    try:
        recording.configure(session)
        staged = staging.prepare(session)
        prompt = request.prepare(session, staged)
        pipeline.assess(session, staged, prompt)
    except ClarifierError as error:
        recording.fail(session, error)
    finally:
        transport.close(session)
        staging.cleanup(session)
        recording.finish(session)
    return recording.report(session)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-test", action="store_true", help="Synthetic transport test; no provider call")
    args = parser.parse_args()
    raise SystemExit(run(args.platform_test))
