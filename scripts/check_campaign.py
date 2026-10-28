#!/usr/bin/env python3
"""Verify/run/compare one declared final campaign; evaluator only, tasks 51–62."""
import argparse
import json

from clarifier import c_preview
from clarifier.inference import recording
from clarifier.outputs import campaign, campaign_metrics
from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError


def run_case(manifest: dict, issue: int, freeze_hash: str) -> int:
    """Run one fresh declared preview with verified boundaries and no retry."""
    case = campaign.select_next(c.ROOT, manifest, issue)
    campaign.record_boundary(c.ROOT, manifest, case, 'before', freeze_hash)
    code = c_preview.run(case_id=issue, id_factory=lambda: case['run_id'])
    campaign.verify_freeze(c.ROOT, freeze_hash)
    campaign.record_boundary(c.ROOT, manifest, case, 'after', freeze_hash)
    campaign.inspect_case(c.ROOT, manifest, case)
    return code


def compare(manifest: dict) -> int:
    """Preserve one final comparison after checking all ten attempts and semantic reviews."""
    folder = c.ROOT / campaign.CAMPAIGN_FOLDER
    expectations = json.loads((c.ROOT / 'evals/golden/expectations.json').read_text())
    expected = {row['issue']: row['decision'] for row in expectations['cases']}
    observations = [campaign.inspect_case(c.ROOT, manifest, row) for row in manifest['cases']]
    reviews = json.loads((folder / 'semantic-reviews.json').read_text())
    rows = [campaign_metrics.compare_case(row, expected[row['issue']], review)
            for row, review in zip(observations, reviews, strict=True)]
    result = campaign_metrics.aggregate(rows, manifest['campaign_id'], manifest['configuration_sha256'])
    recording.save_json(folder / 'comparison.json', result)
    return 0


def main() -> int:
    """Dispatch explicit evaluator steps; failures stop safely without configuration repair."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'run', 'compare'))
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--case', type=int, choices=c.HISTORICAL_CASE_IDS)
    args = parser.parse_args()
    manifest = campaign.verify_freeze(c.ROOT, args.freeze_sha256)
    if args.action == 'run':
        return run_case(manifest, args.case, args.freeze_sha256)
    if args.action == 'compare':
        return compare(manifest)
    print(json.dumps(dict(campaign_id=manifest['campaign_id'], configuration_sha256=manifest['configuration_sha256'], verified=True)))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ClarifierError as error:
        raise SystemExit(str(error)) from None
