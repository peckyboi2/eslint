#!/usr/bin/env python3
"""Milestone B preview only. Serves tasks 09–15 and R1; no posting capability."""
import argparse
from pathlib import Path
from typing import Callable

import constants as c
from errors import ClarifierError
import recording
import request
import routing
import skill
import staging
import transport
import validation


def run(platform_test: bool = False, *, root: Path = c.ROOT,
        clock: Callable[[], str] = recording.utc,
        id_factory: Callable[[], str] = recording.new_run_id) -> int:
    """Run named preview steps and return the recorded CLI exit code."""
    session = recording.start_run(platform_test, root, clock, id_factory)
    try:
        recording.configure(session)
        staged = staging.prepare(session)
        loaded = skill.load_verified(session, staged.workspace)
        prompt = request.prepare(session, staged)
        engine = transport.prepare_engine(session)
        transport.execute(session, staged, loaded, prompt, engine)
        raw = transport.read_result(session)
        result = validation.parse_and_validate(raw)
        route = routing.route_result(result, session.record["run_id"], session.config["model"])
        recording.record_result(session, route)
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
