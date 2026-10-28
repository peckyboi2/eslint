#!/usr/bin/env python3
"""Milestone C no-write dry-run orchestrator for tasks 25–26."""
import argparse
from pathlib import Path
from typing import Callable

import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clarifier.inference import adversarial
from clarifier.shared import constants as c
from clarifier.controls import dry_state
from clarifier.shared.errors import ClarifierError
from clarifier.inference import recording
from clarifier.inference import request
from clarifier.outputs import routing
from clarifier.inference import skill
from clarifier.inference import staging
from clarifier.inference import transport
from clarifier.outputs import validation
from clarifier.github import workflow_io


def prepare(session, attack: str | None):
    """Return staged evidence through the chosen bounded preparer."""
    return adversarial.prepare(session,attack) if attack else staging.prepare(session)


def build_prompt(session, staged, attack: str | None) -> str:
    """Return one approved evidence prompt; expected answers stay outside."""
    return adversarial.prompt(session,staged) if attack else request.prepare(session,staged)


def record_admission(session) -> None:
    """Persist local quota and audit context before secret access/model call."""
    admission=dry_state.reserve(session.root,session.record['run_id'],session.record['input_hashes'])
    recording.save_json(session.folder/'admission.json',admission)
    session.record.update(trigger='Darren-authorised Milestone C local preview',control_configuration=workflow_io.fingerprint(session.root))


def run(attack: str | None=None, *, root: Path=c.ROOT,
        clock: Callable[[],str]=recording.utc,
        id_factory: Callable[[],str]=recording.new_run_id) -> int:
    """Run fresh isolated preview steps; retain typed failures and zero public actions."""
    session=recording.start_run(False,root,clock,id_factory)
    try:
        recording.configure(session)
        staged=prepare(session,attack)
        record_admission(session)
        loaded=skill.load_verified(session,staged.workspace)
        prompt=build_prompt(session,staged,attack)
        engine=transport.prepare_engine(session)
        transport.execute(session,staged,loaded,prompt,engine)
        result=validation.parse_and_validate(transport.read_result(session))
        recording.record_result(session,routing.route_result(result,session.record['run_id'],session.config['model']))
    except ClarifierError as error:
        recording.fail(session,error)
    finally:
        transport.close(session)
        staging.cleanup(session)
        recording.finish(session)
    return recording.report(session)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attack',choices=adversarial.ATTACK_IDS)
    raise SystemExit(run(parser.parse_args().attack))
