# ESLint evaluation plan — research stage

Recorded from the user's accepted review and side-chat proposal on 2026-10-27, Asia/Singapore. This is a research plan, not an implemented evaluation or an additional confirmed assignment requirement.

## Development and regression cases

Use the ten preserved historical reports to define expected behaviour, develop the configuration and check regressions. The expectations were accepted collaboratively before implementation or agent execution.

| Issue | Expected decision |
| --- | --- |
| #19924 | `human_review` |
| #20373 | `clarify` |
| #20606 | `clarify` |
| #19044 | `no_action` |
| #21320 | `no_action` |
| #19477 | `no_action` |
| #21304 | `no_action` |
| #19847 | `no_action` |
| #19118 | `no_action` |
| #19818 | `no_action` |

Detailed rationales and input conditions are in `ESLint expected-decision review.md`. In particular, #19847 and #19118 depend on supplying preserved relevant supporting text from their linked reproduction repositories.

These cases are a purposive development set. Results on them demonstrate behaviour on known examples and regression stability. They do not estimate the prevalence of missing-information reports or establish performance on unseen reports.

## Confirmed execution sequence

Darren confirmed two refinements after the implementation task breakdown:

- Run malicious-input tests in preview before enabling sandbox posting. Include fabricated maintainer approval and poisoned evidence/tool instructions, retain expectations and transcripts, and resolve safeguard failures before enabling posting. The full challenge suite remains a later task.
- After development and control testing, freeze one final configuration and rerun all ten historical cases in preview, explicitly including #20373. Produce the final comparison from that campaign only. Preserve all earlier runs, failures and configuration versions as development history; do not combine outputs from different versions or replace a final failure with an earlier answer.

The freeze records workflow/lockfile, instructions, canonical skill/adapter, scripts, tools, permissions, model/settings and input hashes. A change to the evaluated configuration requires a new freeze and another full ten-case rerun before the final comparison. Provider-version pinning limits and unsuccessful executions remain explicit. See the [implementation task checklist](../IMPLEMENTATION_TASKS.md), especially tasks 25 and 51–62.

## Optional bounded evaluation

If time permits, freeze the developed configuration and evaluate it once on a small batch of previously unseen real reports from a separate, predefined period. Collection and human assessment are additional work. This is one bounded exercise, not ongoing monitoring.

Before collecting the evaluation batch, record the exact period, eligibility rule, sample cap and deterministic selection order. Also define how unavailable historical inputs, previously inspected cases and insufficient eligible cases will be handled. Log every inclusion and exclusion with its reason. Do not replace cases because they are difficult, yield an unfavourable result or fail to contain a desired class of decision.

Freeze the decision rubric, prompts, skills, scripts, model/tool settings and supporting-input policy before examining held-out cases for configuration development. Record the version used. Human expected decisions and reasons must be recorded before the reviewer sees the agent's answers. Use the same historical snapshot and permitted supporting evidence for both assessments; keep later discussion and edited bodies out of agent inputs.

If outputs motivate changes, retain and report the original frozen run. Cases used to tune the revised configuration become development/regression examples; rerunning them does not create a new unseen evaluation.

## Outcomes to examine

- Unnecessary clarification requests: requests where the human expectation is `no_action`, and redundant or irrelevant parts of otherwise justified comments. Record unsupported automatic requests on `human_review` cases separately.
- Missed necessary requests: expected `clarify` cases where the agent stays silent or asks a question that misses the necessary gap. Also report expected `clarify` cases deferred to human review, so deferral cannot be presented as successful automated clarification.
- Human-review frequency: report the count and denominator, plus how these cases compare with human expectations. Silence in `human_review` and `no_action` must remain distinguishable in internal results.
- Review effort: measure time spent establishing expected decisions and reviewing agent outputs separately. Describe the work actually performed; do not infer maintainer time saved without a measured comparison.
- Comment quality and boundaries: a `clarify` label alone is insufficient. The comment must identify a necessary gap and remain within the single-comment scope. Record observed failures and unsuccessful runs separately from decision correctness.

Report raw counts, denominators and a small decision confusion table. State the small-sample limits. If the batch contains no necessary-clarification cases, report that missed-request performance could not be assessed rather than choosing replacement cases to create a favourable balance.

## Scope and open decisions

All processing and test comments remain in the user's sandbox. No upstream changes or contact with original reporters are authorised by this plan. Submitted reproduction code is read as evidence rather than executed by this agent.

Still undecided: whether time permits the additional exercise, exact period, sample size, final eligibility/selection rules, treatment of unavailable historical evidence and how review effort will be timed. No additional batch has been collected or labelled, and no agent configuration or evaluation run has been created.
