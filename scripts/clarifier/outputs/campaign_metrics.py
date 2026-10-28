"""Pure evaluator comparison with explicit failures/denominators. Serves task 62."""
from clarifier.outputs.campaign import CampaignError, require
from clarifier.shared import constants as c
from clarifier.shared.errors import guarded

QUALITY_STATES = ('pass', 'fail', 'not_assessable')
REVIEW_FLAGS = ('irrelevant_content', 'redundant_content', 'silent_branch_violation')


@guarded(CampaignError, 'Malformed evaluator comparison')
def compare_case(observation: dict, expected: str, review: dict) -> dict:
    """Return decision/content findings or raise CampaignError for incomplete evaluator review."""
    require(review['issue'] == observation['issue'] and review['run_id'] == observation['run_id'], 'Review binding differs')
    require(review['comment_quality'] in QUALITY_STATES, 'Missing comment review')
    require([row['criterion'] for row in review['criteria']] == list(range(1, 8)), 'Missing frozen quality criteria')
    require(all(row['result'] in QUALITY_STATES and row['evidence'] for row in review['criteria']), 'Incomplete criterion evidence')
    require(all(type(review[key]) is bool for key in REVIEW_FLAGS), 'Missing content/silence flags')
    completed = observation['status'] == 'completed'
    actual = observation['actual_decision']
    require(completed == (actual in c.ALLOWED_DECISIONS), 'Execution failure has a substituted decision')
    require((actual == c.CLARIFY) == (review['comment_quality'] != 'not_assessable'), 'Comment quality applicability differs')
    return {**observation, 'expected_decision': expected, 'decision_pass': completed and actual == expected,
            'quality_review': review, 'clarification_success': completed and actual == c.CLARIFY
            and expected == c.CLARIFY and review['comment_quality'] == 'pass'}


def count(rows: list[dict], predicate) -> int:
    """Return the number of observations matching one explicit metric predicate."""
    return sum(bool(predicate(row)) for row in rows)


def measure(numerator: int, denominator: int) -> dict:
    """Return raw counts without hiding unavailable or zero-sized denominators."""
    return dict(count=numerator, denominator=denominator)


@guarded(CampaignError, 'Malformed campaign aggregation')
def aggregate(rows: list[dict], campaign_id: str, configuration: str) -> dict:
    """Return three-way confusion and separate quality/deferral metrics; reject mixed campaigns."""
    require([row['issue'] for row in rows] == list(c.HISTORICAL_CASE_IDS), 'Incomplete/duplicate ten-case comparison')
    require(all(row['campaign_id'] == campaign_id and row['configuration_sha256'] == configuration for row in rows), 'Mixed campaigns/configurations')
    matrix = {expected: {actual: 0 for actual in c.ALLOWED_DECISIONS} for expected in c.ALLOWED_DECISIONS}
    for row in rows:
        if row['status'] == 'completed':
            matrix[row['expected_decision']][row['actual_decision']] += 1
    completed = count(rows, lambda r: r['status'] == 'completed')
    clarify = count(rows, lambda r: r['actual_decision'] == c.CLARIFY)
    metrics = metric_counts(rows, completed, clarify)
    return dict(campaign_id=campaign_id, configuration_sha256=configuration, cases=rows,
                confusion=matrix, metrics=metrics, execution_failures=[r['issue'] for r in rows if r['status'] != 'completed'],
                always_no_action_baseline=measure(7, 10), review_required=True, promotion_allowed=False,
                interpretation='Known purposive development/regression examples; no unseen or representative performance claim. Assistant content review is not Darren independent approval. September 0/10 is a separate measurement. No workload/time-savings or deployment-readiness claim.')


def metric_counts(rows: list[dict], completed: int, clarify: int) -> dict:
    """Return separate denominator-bearing decision, execution, silence and comment metrics."""
    expected_count = lambda decision: count(rows, lambda r: r['expected_decision'] == decision)
    correct = count(rows, lambda r: r['decision_pass'])
    return dict(
        completed=measure(completed, len(rows)), decision_matches=measure(correct, len(rows)),
        decision_matches_completed=measure(correct, completed),
        unnecessary_requests_on_complete=measure(count(rows, lambda r: r['expected_decision'] == c.NO_ACTION and r['actual_decision'] == c.CLARIFY), expected_count(c.NO_ACTION)),
        unsupported_requests_on_human_review=measure(count(rows, lambda r: r['expected_decision'] == c.HUMAN_REVIEW and r['actual_decision'] == c.CLARIFY), expected_count(c.HUMAN_REVIEW)),
        missed_necessary_clarifications=measure(count(rows, lambda r: r['expected_decision'] == c.CLARIFY and not r['clarification_success']), expected_count(c.CLARIFY)),
        clarify_deferred_to_human=measure(count(rows, lambda r: r['expected_decision'] == c.CLARIFY and r['actual_decision'] == c.HUMAN_REVIEW), expected_count(c.CLARIFY)),
        all_deferrals=measure(count(rows, lambda r: r['actual_decision'] == c.HUMAN_REVIEW), len(rows)),
        silent_branch_violations=measure(count(rows, lambda r: r['quality_review']['silent_branch_violation']), count(rows, lambda r: r['actual_decision'] in (c.NO_ACTION, c.HUMAN_REVIEW))),
        public_writes=measure(count(rows, lambda r: r['public_actions'] != []), len(rows)),
        comment_quality_passes=measure(count(rows, lambda r: r['quality_review']['comment_quality'] == 'pass'), clarify),
        irrelevant_comments=measure(count(rows, lambda r: r['quality_review']['irrelevant_content']), clarify),
        redundant_comments=measure(count(rows, lambda r: r['quality_review']['redundant_content']), clarify))
