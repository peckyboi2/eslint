"""Shared isolated decision sequence for historical/live staging. Serves B03."""
from clarifier.inference import recording, skill, transport
from clarifier.outputs import routing, validation


def assess(session, staged, prompt: str, *, engine_setup=None, execute=None) -> None:
    """Record one restricted decision or raise ClarifierError at the caller boundary."""
    loaded = skill.load_verified(session, staged.workspace)
    engine = (engine_setup or transport.prepare_engine)(session)
    (execute or transport.execute)(session, staged, loaded, prompt, engine)
    raw = transport.read_result(session)
    result = validation.parse_and_validate(raw)
    route = routing.route_result(result, session.record['run_id'], session.config['model'],
                                 source_issue=session.record['source_issue'],
                                 trusted_live=session.record.get('trigger')=='issues:opened')
    recording.record_result(session, route)
