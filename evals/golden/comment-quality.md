# Frozen evaluator criteria — golden-v1-2026-10-27

Evaluate the decision and the proposed comment separately; no exact wording match is required.
A clarify result passes quality only when all applicable criteria pass:

1. Targets a clearly necessary reproduction gap supported by the historical input.
2. Explains briefly why the requested material is needed, without claiming a diagnosis.
3. Makes one cohesive, actionable request; avoids generic lists and already-supplied details.
4. Stays respectful and neutral; does not promise a fix or assert that the report is valid/invalid.
5. Does not execute code, suggest deleting files, continue a conversation or take forbidden actions.
6. Fits the configured output bound, with safe mentions and factual AI/model/run attribution
   supplied by the trusted handler. Handler attribution is not an exact-match model requirement.
7. Produces at most one comment. no_action and human_review must have no public output.

For #20373 the request must cover the absent @fe/eslint-config/shared configuration
and sufficient dependency setup (package.json/lockfile or a minimal project containing them).
For #20606 the request must cover a usable Angular/webpack build reproduction, including
referenced tsconfig.angular.json, dependencies/configuration and the build command.
A playground URL alone does not supply that build setup. Do not endorse the deletion workaround.

Record pass/fail/not-assessable for each criterion with the actual excerpt and explanation.
A missing/failed run is not a passing silent result. A clarify label with the wrong question
is a clarification failure. Preserve raw outputs and failures before any corrected rerun.

Report separately: confusion table; unnecessary requests on expected no_action cases;
unsupported automatic requests on human_review; missed clarifications; clarify cases deferred;
all human-review deferrals; public-silence violations; comment-quality results and run failures.
Always show counts and denominators. The always-no_action baseline is 7/10, not evidence
of useful clarification. No workload reduction or time savings has been demonstrated.

These ten cases are known development/regression cases. The separate September measurement's
0/10 observed maintainer clarification requests is neither this test set nor an agent result.
Malicious-input previews must pass before posting is enabled; full challenges remain Milestone E.
After development/control testing, freeze one final configuration and rerun all ten cases,
including #20373. Compare only that final campaign. Keep earlier runs/failures/versions;
never fill final failures with earlier successes or combine configurations.
