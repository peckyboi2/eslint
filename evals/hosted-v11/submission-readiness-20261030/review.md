# Submission readiness review — 30 October 2026

The submission is the controlled `peckyboi2/eslint` fork, with [SUBMISSION.md](../../../SUBMISSION.md) as its entry point. The current hosted runtime is `hosted-preview-v11-artifacts-v2`. This review covers documentation, evidence integrity and offline controls; it makes no fresh model judgement or provider request.

## Requirements and evidence

| Updated brief requirement | Location and assessment |
| --- | --- |
| Real open-source workflow, AI rationale, measured need and rejected alternative | [DESIGN](../../../DESIGN.md) and [September measurement](../../measurement/README.md). The separate 0/10 observed clarification-request rate and response-time metric are reported with their period and limitations; no time-saving claim is made. |
| Workflow trigger, permissions, tools, output limits and timeout | [Automatic workflow](../../../.github/workflows/clarifier-triage.yml), [policy](../../../scripts/clarifier/controls/policy.py) and [hosted transport](../../../scripts/clarifier/inference/hosted_transport.py). GitHub Actions is the stated platform equivalent; a gh-aw lockfile does not apply. |
| Repository instructions and contribution policy | [AGENTS](../../../AGENTS.md) and [CONTRIBUTING](../../../CONTRIBUTING.md) cover repository facts, tests, conventions, forbidden actions and AI-assisted contributions. |
| Claude-format skill, supporting checks and verified use | [Canonical skill](../../../.claude/skills/eslint-clarification/SKILL.md), [native loader](../../../scripts/clarifier/inference/skill.py) and saved native-loading/request evidence in each hosted attempt. Codex is the execution engine. |
| Sandbox controlled by the student | [Automatic-opening evidence](../live-smoke-artifacts-v2-20261029/README.md) records a genuine fork issue event, admission, hosted inference and complete artifact upload. |
| At least ten real historical inputs and pre-recorded expectations | [Prepared inputs](../../golden/prepared-inputs/manifest.json), [expectations](../../golden/expectations.json) and [accepted reasons](../../golden/expected-decision-review.md). Expectations remain 2 clarify / 7 no_action / 1 human_review. |
| Actual output, comparison, all failures and test logs | [Current hosted results](../../golden/hosted-v11-20261029/README.md) link all ten historical attempts and three attacks, original artifacts, comparisons, transcripts and logs. Historical result is 9/10; #19924 remains a failed match. |
| Adversarial input, including fabricated maintainer approval | Three separately recorded attacks matched expectations, with zero tools/public actions. Malicious tool instructions were simulated text; no live MCP was connected. |
| Nine governance controls and five scenario answers | [DESIGN](../../../DESIGN.md) names implementation/evidence paths and distinguishes implemented, simulated, unsupported and untested controls. |
| Agent bill of materials and final AI-use statement | [DESIGN](../../../DESIGN.md) identifies engine/model pins and limits, instructions, tools/MCP, permissions, sources, logs, evaluations and responsible humans. The incoming user-authored review statement is retained unchanged. |
| DESIGN at most 150 lines | Current file has 75 lines, including headings and blanks. |
| Reproduction instructions | [Offline verification](../../../SUBMISSION.md#offline-verification) uses full Git history and Python 3.11+, with no provider key, CLI binary, network or submitted-code execution. It validates saved evidence, not fresh semantic judgement. |
| Specific GitHub commit through eLearn | Commit and push the complete checked tree, then submit its immutable commit URL. Later commits will not be marked. No PDF is required. GitHub reported the repository public during this review; collaborator access is required only if it becomes private. |

## Corrections in this review

The initial offline check failed with `Candidate hash mismatch: SUBMISSION.md`; the [literal failure record](initial-verification-failure.json) and incoming candidate/guides are preserved alongside this review. The current submission guide gains working replacement routes for four frozen research links and the exact eLearn submission instructions. The hosted guide now distinguishes standing authorization for eligible automatic issue previews from authorization for new standalone evaluation/test campaigns. The working-folder README outside the submitted fork now identifies v11 as current and labels the earlier material as history.

The existing DESIGN edit and 29 October guide-update records are preserved. Only the current documentation/review manifest is refreshed. Evaluated runtime/configuration, canonical skill, expectations, original attempts, failures and ledger receipts retain their identities. No inference campaign, quota extension, remote publication or workflow change is part of this review.

The first staged diff check detected the incoming submission guide's original trailing blank line in its preserved snapshot. The [failure](staged-diff-check-initial.txt) is retained; an exact-path `.gitattributes` rule preserves that snapshot's bytes and exempts only it from whitespace checking. Current guides still receive normal checks. The [index-packaging record](index-packaging.json) identifies this correction.

## Verification

All four documented commands passed against the refreshed documentation tree. The [complete-tree result](verification.json), [49 verifier tests](verifier-tests.txt), [236 safety tests](safety-tests.txt) and [safety-test stdout](safety-test-stdout.txt) are retained. The safety stdout contains synthetic rejection receipts; it is not a single JSON document. `git diff --check` passed. The three current guides also passed a 73-link local navigation check and Markdown-spacing check. Run from the repository root:

```sh
python3 -B scripts/verify_submission.py
python3 -B -m unittest discover -s scripts/automatic_tests -v
python3 -B scripts/verify_automatic.py --tests
git diff --check
```

These checks verify source/evidence identities and tested infrastructure. The current hosted campaign reports 13 requests, 74,762 tokens, 9/10 historical matches and 3/3 adversarial matches; the two clarification wording reviews are assistant assessments. Earlier test logs and results remain part of the campaign bundle. The [readiness update record](update.json) identifies this review's checked files and logs. The saved full-tree result identifies the [checked documentation manifest](checked-documentation-candidate.json), before these check logs were exported. The current manifest additionally binds the exported logs and finished review; a final complete-tree check is required after packaging and in the selected commit's clean checkout.

## Remaining human steps and limitations

Review the final material and be ready to explain the skill, trigger/admission flow, permission boundary, evaluation method and #19924's failure. The brief permits reported failures; a wrong decision must remain visible. Phone stopping, live cancellation/queue overflow, provider termination and host OS/firewall containment remain unverified. No representative accuracy or workload reduction is established.

Darren retains responsibility for pushing and eLearn submission. Include all current documentation and readiness records in the selected commit, verify that exact commit in a clean checkout, push it, then open the commit URL and check all required files before submitting the one link. The pre-review HEAD omits the current working-tree edits, so its URL is not a link to this finished preparation.
