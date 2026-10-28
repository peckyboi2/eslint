"""Strict pure ledger validation for tasks 17–18 and 21–22."""
from copy import deepcopy
import json
import re
from typing import Any

from clarifier.controls import policy as p

STATE_KEYS = {'schema', 'enabled', 'posting_enabled', 'campaign', 'admissions', 'posts', 'decisions'}
ADMISSION_KEYS = {'run_id', 'event_key', 'input_key', 'at', 'campaign'}
POST_KEYS = {'report', 'input_key', 'event_key', 'marker', 'run_id', 'status', 'comment_id', 'configuration'}
DECISION_KEYS = {'actor_id', 'at', 'reason', 'action'}
CAMPAIGN = 'c-development-20261028'
POST_STATUSES = ('reserved', 'uncertain', 'posted')


def check(ok: bool, message: str) -> None:
    """Raise StateError for a failed ledger invariant."""
    if not ok:
        raise p.StateError(message)


def digest(value: Any) -> bool:
    """Return whether a value is a canonical SHA-256."""
    return isinstance(value, str) and re.fullmatch(p.SHA_PATTERN, value) is not None


def integer(value: Any) -> bool:
    """Return whether a value is a nonnegative integer, excluding booleans."""
    return type(value) is int and value >= 0


def initial(at: int, reason: str) -> dict:
    """Return disabled initial state; raise StateError for an unauditable decision."""
    state = dict(schema=1, enabled=False, posting_enabled=False, campaign=CAMPAIGN,
                 admissions=[], posts=[], decisions=[dict(actor_id=p.OWNER_ID, at=at, reason=reason, action='bootstrap')])
    return validate(state)


def validate(state: Any) -> dict:
    """Return a detached validated ledger or raise StateError; never repair it."""
    check(isinstance(state, dict) and set(state) == STATE_KEYS, 'Missing/unknown ledger fields')
    check(type(state['schema']) is int and state['schema'] == 1, 'Unsupported ledger schema')
    check(type(state['enabled']) is bool and type(state['posting_enabled']) is bool, 'Invalid enable state')
    check(state['campaign'] == CAMPAIGN, 'Unapproved campaign reset')
    for name in ('admissions', 'posts', 'decisions'):
        check(isinstance(state[name], list), 'Invalid record collection')
    validate_decisions(state['decisions'])
    validate_admissions(state['admissions'], local_campaign_limit(state))
    validate_posts(state['posts'], state['admissions'])
    mode = next(row['action'] for row in reversed(state['decisions']) if row['action'] in ('bootstrap','disable','enable-preview','enable-posting'))
    flags = {'bootstrap': (False, False), 'disable': (False, False), 'enable-preview': (True, False), 'enable-posting': (True, True)}
    check((state['enabled'], state['posting_enabled']) == flags[mode], 'Enabled flags lack matching accountable decision')
    return deepcopy(state)


def local_campaign_limit(state: dict) -> int:
    """Return the recorded local cap or the unchanged hosted campaign cap."""
    approved = any(row['action'] == 'extend-local-preview'
                   and row['reason'].startswith(p.LOCAL_EXTENSION_REASON)
                   and digest(row['reason'][len(p.LOCAL_EXTENSION_REASON):]) for row in state['decisions'])
    return p.LOCAL_CAMPAIGN_LIMIT if approved else p.CAMPAIGN_LIMIT


def validate_admissions(rows: list, limit: int = p.CAMPAIGN_LIMIT) -> None:
    """Raise StateError for corrupt/duplicate quota reservations."""
    events, runs = set(), set()
    for row in rows:
        check(isinstance(row, dict) and set(row) == ADMISSION_KEYS, 'Invalid admission fields')
        check(isinstance(row['run_id'], str) and re.fullmatch(p.RUN_PATTERN, row['run_id']) is not None, 'Invalid admitted run')
        check(digest(row['event_key']) and digest(row['input_key']) and integer(row['at']), 'Invalid admission value')
        check(row['campaign'] == CAMPAIGN, 'Unknown admitted campaign')
        check(row['event_key'] not in events and row['run_id'] not in runs, 'Duplicate reservation')
        events.add(row['event_key']); runs.add(row['run_id'])
    check(len(rows) <= limit, 'Campaign ledger exceeds quota')


def validate_posts(rows: list, admissions: list) -> None:
    """Raise StateError for inconsistent or duplicate lifetime posting intents."""
    reports, markers = set(), set()
    for row in rows:
        check(isinstance(row, dict) and set(row) == POST_KEYS, 'Invalid posting fields')
        check(type(row['report']) is int and row['report'] > 0 and row['report'] not in reports, 'Duplicate/invalid lifetime report')
        check(digest(row['input_key']) and digest(row['event_key']) and digest(row['configuration']), 'Invalid posting identity')
        check(isinstance(row['marker'], str) and re.fullmatch(r'clarifier-attempt-[a-f0-9]{64}', row['marker']) is not None, 'Invalid attempt marker')
        check(row['marker'] not in markers and row['status'] in POST_STATUSES, 'Invalid posting status/marker')
        check((row['status'] == 'posted' and type(row['comment_id']) is int and row['comment_id'] > 0) or (row['status'] != 'posted' and row['comment_id'] is None), 'Invalid comment receipt')
        check(any(a['run_id'] == row['run_id'] and a['input_key'] == row['input_key'] and a['event_key'] == row['event_key'] for a in admissions), 'Posting lacks admission')
        reports.add(row['report']); markers.add(row['marker'])


def validate_decisions(rows: list) -> None:
    """Raise StateError unless accountable decision records are retained."""
    check(bool(rows), 'Missing accountable decision')
    for row in rows:
        check(isinstance(row, dict) and set(row) == DECISION_KEYS, 'Invalid decision fields')
        check(row['actor_id'] == p.OWNER_ID and integer(row['at']), 'Invalid decision authority/time')
        check(isinstance(row['reason'], str) and 1 <= len(row['reason']) <= 1000, 'Missing decision reason')
        check(row['action'] in ('bootstrap', 'enable-preview', 'enable-posting', 'disable', 'reconcile', 'extend-local-preview'), 'Unknown decision')
    check(rows[0]['action'] == 'bootstrap', 'Missing initial decision')


def encode(state: dict) -> bytes:
    """Return canonical bounded state bytes or raise StateError."""
    data = (json.dumps(validate(state), sort_keys=True, separators=(',', ':'))+'\n').encode()
    check(len(data) <= p.MAX_LEDGER_BYTES, 'Ledger exceeds bound')
    return data


def decode(data: bytes) -> dict:
    """Return strictly parsed state or raise StateError on malformed/duplicate keys."""
    check(len(data) <= p.MAX_LEDGER_BYTES, 'Ledger exceeds bound')
    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, 'Duplicate state key')
            result[key] = value
        return result
    try:
        return validate(json.loads(data, object_pairs_hook=pairs))
    except (ValueError, TypeError, UnicodeError):
        raise p.StateError('Malformed ledger JSON') from None


def validate_transition(previous: dict, updated: dict) -> None:
    """Reject removal/rewrite of quota, decisions or lifetime intents across commits."""
    previous,updated=validate(previous),validate(updated)
    for field in ('admissions','decisions'):
        check(updated[field][:len(previous[field])]==previous[field], 'Append-only history changed')
    by_report={row['report']:row for row in updated['posts']}
    for old in previous['posts']:
        check(old['report'] in by_report, 'Lifetime intent removed')
        new=by_report[old['report']]
        stable=POST_KEYS-{'status','comment_id'}
        check(all(old[key]==new[key] for key in stable), 'Posting identity rewritten')
        if old['status']=='posted': check(old==new, 'Posted receipt rewritten')
        if old['status']=='uncertain':
            check(new==old or (new['status']=='posted' and len(updated['decisions'])>len(previous['decisions']) and updated['decisions'][-1]['action']=='reconcile'), 'Uncertain result requires accountable reconciliation')
