#!/usr/bin/env python3
"""Surface one golden regression for owner review; evaluator-only task 49 tool."""
import argparse
from pathlib import Path
import re

from clarifier.inference.recording import save_json, sha
from clarifier.inference.staging import read_safe
from clarifier.outputs.validation import parse_json
from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError, guarded

EXPECTATIONS_SHA256 = 'c3a3b2525fe8d4c11da72878a7b201568aeb461f849403d76091a2bca7bcad48'
OBSERVATION_KEYS = {'issue', 'decision', 'configuration_sha256', 'model', 'status', 'quality_review', 'public_actions'}
STATUSES = ('completed', 'failed', 'interrupted', 'invalid_output')
QUALITY_REVIEWS = ('pass', 'fail', 'pending')
SHA_PATTERN = r'[a-f0-9]{64}'


class RegressionError(ClarifierError):
    """An evaluator observation cannot be trusted or compared."""


@guarded(RegressionError, 'Cannot load frozen evaluator expectations')
def load_expectations(root: Path = c.ROOT) -> dict[int, str]:
    """Return untouched golden-v1 decisions or raise RegressionError on drift."""
    folder = root / 'evals/golden'
    raw = read_safe(folder, 'expectations.json', c.MAX_INPUT_BYTES)
    if sha(raw) != EXPECTATIONS_SHA256:
        raise RegressionError('Frozen expectations changed; comparison blocked')
    return {row['issue']: row['decision'] for row in parse_json(raw.decode())['cases']}


@guarded(RegressionError, 'Malformed regression observation')
def validate_observation(value: dict) -> dict:
    """Return a bounded observation or raise RegressionError, never repair it."""
    valid = isinstance(value, dict) and set(value) == OBSERVATION_KEYS
    if not valid or type(value['issue']) is not int or value['issue'] not in c.HISTORICAL_CASE_IDS:
        raise RegressionError('Invalid regression target or fields')
    if value['decision'] not in (*c.ALLOWED_DECISIONS, None) or value['status'] not in STATUSES:
        raise RegressionError('Invalid result/status')
    if not re.fullmatch(SHA_PATTERN, value['configuration_sha256']):
        raise RegressionError('Invalid configuration identity')
    if not isinstance(value['model'], str) or not 0 < len(value['model']) <= 200:
        raise RegressionError('Invalid model identity')
    if value['quality_review'] not in QUALITY_REVIEWS or not isinstance(value['public_actions'], list):
        raise RegressionError('Missing quality/public-action review')
    return dict(value)


@guarded(RegressionError, 'Cannot load bounded regression observation')
def load_observation(path: Path) -> dict:
    """Return one owner-selected observation or raise a typed read/schema error."""
    raw = read_safe(path.parent, path.name, c.MAX_INPUT_BYTES)
    return validate_observation(parse_json(raw.decode()))


@guarded(RegressionError, 'Malformed regression reference')
def assess(expectations: dict[int, str], observation: dict, configuration: str, model: str) -> dict:
    """Return explicit review findings; never authorise promotion or estimate accuracy."""
    observed = validate_observation(observation)
    if not re.fullmatch(SHA_PATTERN, configuration) or observed['issue'] not in expectations:
        raise RegressionError('Missing reference configuration/expectation')
    expected = expectations[observed['issue']]
    checks = {'decision mismatch': observed['decision'] == expected,
              'configuration changed': observed['configuration_sha256'] == configuration,
              'model identity changed': observed['model'] == model,
              'execution incomplete': observed['status'] == 'completed',
              'quality review missing/failed': observed['quality_review'] == 'pass',
              'unexpected public action': observed['public_actions'] == []}
    failures = [reason for reason, passed in checks.items() if not passed]
    return dict(issue=observed['issue'], expected_decision=expected, observation=observed,
                checks_pass=not failures, failures=failures, review_required=True,
                review_owner='Darren Peck', promotion_allowed=False,
                scope='One evaluator observation; no campaign accuracy claim',
                provider_revision_detection='Unavailable when provider retains the same model ID')


def arguments() -> argparse.Namespace:
    """Return explicit evaluator paths/reference configuration; no default model run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observation', type=Path)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--model', default=c.FIXED_CONFIG['model'])
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Compare one fixture and preserve a new review report; no inference or writes to GitHub."""
    args = arguments()
    expected = load_expectations()
    observed = load_observation(args.observation)
    report = assess(expected, observed, args.configuration, args.model)
    save_json(args.output, report)
    return int(not report['checks_pass'])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ClarifierError as error:
        raise SystemExit(str(error)) from None
