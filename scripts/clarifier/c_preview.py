#!/usr/bin/env python3
"""Quota-guarded no-write historical/attack preview. Serves tasks 25–38."""
import argparse
from pathlib import Path
from typing import Callable

import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clarifier.inference import adversarial
from clarifier.shared import constants as c
from clarifier.controls import dry_state
from clarifier.shared.errors import ClarifierError, StagingError
from clarifier.inference import packages
from clarifier.inference import recording
from clarifier.inference import request
from clarifier.outputs import routing
from clarifier.inference import skill
from clarifier.inference import staging
from clarifier.inference import transport
from clarifier.outputs import validation
from clarifier.github import workflow_io


def prepare(session, attack: str | None, case_id: int):
    """Return staged evidence through the chosen bounded preparer."""
    if attack and case_id != c.SOURCE_ISSUE:
        raise StagingError('Attack and historical case selectors cannot be combined')
    return adversarial.prepare(session,attack) if attack else staging.prepare(session, packages.load(case_id, session.root))


def build_prompt(session, staged, attack: str | None) -> str:
    """Return one approved evidence prompt; expected answers stay outside."""
    return adversarial.prompt(session,staged) if attack else request.prepare(session,staged)


def record_admission(session) -> None:
    """Persist local quota and audit context before secret access/model call."""
    admission=dry_state.reserve(session.root,session.record['run_id'],session.record['input_hashes'])
    recording.save_json(session.folder/'admission.json',admission)
    session.record.update(control_configuration=workflow_io.fingerprint(session.root),
                          inference_admitted=True, kind='actual Codex ChatGPT dry run',
                          verification_type='model dry run')


def run(attack: str | None=None, *, case_id: int=c.SOURCE_ISSUE, root: Path=c.ROOT,
        clock: Callable[[],str]=recording.utc,
        id_factory: Callable[[],str]=recording.new_run_id) -> int:
    """Run fresh isolated preview steps; retain typed failures and zero public actions."""
    session=recording.start_run(False,root,clock,id_factory,source_issue=case_id)
    try:
        recording.mark_local_attempt(session)
        recording.configure(session)
        staged=prepare(session,attack,case_id)
        prompt=build_prompt(session,staged,attack)
        record_admission(session)
        loaded=skill.load_verified(session,staged.workspace)
        engine=transport.prepare_engine(session)
        transport.execute(session,staged,loaded,prompt,engine)
        result=validation.parse_and_validate(transport.read_result(session))
        recording.record_result(session,routing.route_result(result,session.record['run_id'],session.config['model'],source_issue=session.record['source_issue']))
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
    parser.add_argument('--case',type=int,choices=c.HISTORICAL_CASE_IDS,default=c.SOURCE_ISSUE)
    args=parser.parse_args()
    raise SystemExit(run(args.attack,case_id=args.case))
