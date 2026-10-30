# Assignment 3: automatic ESLint clarification previews

This controlled ESLint fork configures Codex CLI to assess whether bug reports contain enough reproduction information. The normal workflow starts automatically when a new issue opens. Results are internal previews: the agent can suggest one clarification, take no action, or defer to human review. It cannot publish comments or change issues/PRs through this route.

The workflow uses GitHub Actions as the platform equivalent to a GitHub Agentic Workflow; no gh-aw compiler or compiled `.lock.yml` applies. The root README describes upstream ESLint. This file is the assignment entry point.

## Look through order

1. [DESIGN.md](DESIGN.md) - workflow justification, governance controls, five scenario answers, limitations, bill of materials and AI-use statement. Check the separate [September measurement](evals/measurement/README.md) for the period, method and limitations of the repository data.
2. [AGENTS.md](AGENTS.md),  [canonical skill](.claude/skills/eslint-clarification/SKILL.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for repository facts, the decision procedure and contribution policy.
3. Inspect the [automatic workflow](.github/workflows/clarifier-triage.yml), [stop workflow](.github/workflows/clarifier-stop.yml) and [blocked approval workflow](.github/workflows/clarifier-approve.yml). Check permissions and enforced restrictions rather than relying on prose.
4. Follow [workflow.py](scripts/clarifier/workflow.py) into [automatic intake](scripts/clarifier/github/intake_io.py), then the [inference pipeline](scripts/clarifier/inference/pipeline.py). Inspect [admission](scripts/clarifier/controls/admission.py), [policy](scripts/clarifier/controls/policy.py), [skill loading](scripts/clarifier/inference/skill.py), the [hosted gateway](scripts/clarifier/inference/hosted_transport.py) and [output validation](scripts/clarifier/outputs/validation.py).
5. Use the [current evaluation results table](evals/golden/hosted-v11-20261029/README.md) to inspect all ten historical cases and three attacks. The [evaluation index](evals/golden/INDEX.md) also links original expectations, inputs and earlier evidence. Compare actual answers with pre-recorded expectations, including the failed case.

The frozen prepared-input guide retains three links to its original working-folder layout. Within this repository, use the [accepted decision review](evals/golden/expected-decision-review.md) for both references to `ESLint expected-decision review.md`, and the [prepared-input manifest](evals/golden/prepared-inputs/manifest.json), [snapshot boundaries](evals/golden/prepared-inputs/README.md#snapshot-boundaries) and per-case `snapshot.json` files for provenance. The [completed hosted campaign](evals/hosted-v11/campaign-20261029/README.md) records the final freeze, execution and checks. The original research evaluation plan remains in Git history.

## How the automatic workflow operates

1. A new issue in `peckyboi2/eslint` triggers **Sandbox clarification preview** through `issues: opened`. The gate admits only eligible User-authored `Bug:` reports in the pinned sandbox/main, with matching event/API identities and unchanged input.
2. Admission reserves quota in the append-only `triage-state` ledger before inference. Duplicate original issue IDs, reruns, disabled state and exhausted quotas are rejected; admitted failures retain their reservation.
3. The inference job installs the hash-pinned Linux Codex CLI, loads the verified canonical skill and assesses a closed input package through one bounded hosted provider request. Model tools and MCP servers are absent. Provider credentials stay in the trusted gateway; the native model process receives no GitHub or provider credential.
4. Trusted code validates the decision schema and routes the result into a saved artifact. `clarify` contains one attributed proposed question; `no_action` and `human_review` contain no proposed comment. Every branch remains publicly silent.
5. Maintainers inspect **Actions → Sandbox clarification preview → run → Artifacts → preview-<run ID>**. Review the raw answer, validated decision, run record, request, native skill-loading evidence and transcript. Human review is required before using a proposal in a contribution.

Default permissions are empty. Gate/inference receive read permissions; only the separate admission job gets contents-write for durable state. Automatic intake has no issues-write permission or posting job. Issue closure/deletion, PR merging, force-pushing, submitted-code execution and upstream contact are outside the model's available capabilities. Host OS/firewall containment is not claimed.

Normal limits are **10 admissions per rolling 24 hours** and **20 per campaign**, one provider request per inference and a 15-minute inference job timeout. The provider call has a 300-second bound. No automatic retry, quota refund or delayed backlog drain is installed.

At the recorded campaign completion on 29 October 2026, the automatic preview and independent stop workflows were enabled. The approval and manual evaluation workflows were disabled. The repository secret `CLARIFIER_PROVIDER_KEY` supplies hosted inference; its value is not stored in the submission.

## Current evaluation and what it proves

The [frozen hosted campaign](evals/hosted-v11/campaign-20261029/README.md) used the original ten historical inputs and three additional adversarial inputs, once each. Historical expectations remained **2 clarify / 7 no_action / 1 human_review**, recorded before inference. Snapshots, supporting files, cutoffs and provenance are preserved; evaluator answers and later discussion were excluded from requests. Submitted reproductions were not executed.

| Evidence | Result and interpretation |
| --- | --- |
| Historical decisions | **9/10** matched; always-no_action baseline **7/10**. |
| Known failure | **#19924:** expected `human_review`, actual `no_action`. Silence does not make the decision correct. |
| Expected clarification wording | **2/2** passed the original criteria in assistant review; this is not independent human validation. |
| Adversarial cases | **3/3** matched: fabricated maintainer approval, poisoned support and simulated malicious tool instructions. No live MCP server was connected. |
| Execution and usage | **13 provider requests**, **74,762 tokens**, zero model tool calls and zero public actions. Cost is unavailable. |
| Infrastructure/evidence checks | [236 safety tests](evals/hosted-v11/campaign-20261029/safety-tests-preflight.txt) and [49 verifier tests](evals/hosted-v11/campaign-20261029/verifier-tests-final.txt) passed; these do not establish semantic correctness. |

The [results table](evals/golden/hosted-v11-20261029/README.md) links every original output, record, transcript, assistant assessment and GitHub run. The [comparison](evals/golden/hosted-v11-20261029/comparison.json) reports all outcomes and confusion counts. Start with #20373 for a necessary clarification, #19044 for intentionally blank configuration and #19924 for the uncertainty failure, then inspect the remaining cases and attacks.

The historical campaign used a separate owner-only [manual replay workflow](.github/workflows/clarifier-evaluate.yml), not thirteen new issue-opening events. It exercised the same frozen hosted inference runtime, canonical skill and API gateway. The [automatic-opening test](evals/hosted-v11/live-smoke-artifacts-v2-20261029/README.md) separately demonstrates the actual GitHub opening trigger, gate/admission/inference, native skill loading and complete artifact upload: one request, `human_review`, 2,910 tokens, all 26 original artifact hashes verified and no comments. Its checks establish integration, not historical decision accuracy.

The owner approved a temporary **10 admissions/60 seconds** window only for the 13-run manual evaluation. The automatic issue workflow retained its 24-hour window throughout. [Restoration receipts](evals/hosted-v11/campaign-20261029/restoration.json) show the evaluation setting restored to `86400` and the manual evaluator disabled. At completion, all **15 hosted reservations** remained (two opening tests plus thirteen evaluations), leaving five runs under the total budget. The normal daily limit can block further admission until reservations age out; historical reservations are not reset or refunded.

These are known development/regression cases, not an unseen or representative sample. The separate September measurement is not their evaluation result. No representative accuracy, workload reduction or time saving is established. DESIGN and the case records document provenance limitations, the retained semantic failure and remaining untested controls.

## Offline verification

Use Git with the repository's full history and Python 3.11+ (standard library only). Run from this repository root:

```sh
python3 -B scripts/verify_submission.py
python3 -B -m unittest discover -s scripts/automatic_tests -v
python3 -B scripts/verify_automatic.py --tests
git diff --check
```

These commands make no model/provider request and execute no submitted reproduction. They require no API key, Codex binary or Node installation. The first command checks the complete current tree, frozen source/input identities, original artifact hashes including hidden SKILL.md, native loading, actual provider output, comparison, durable reservations and quota restoration. Inspect `current_hosted_evaluation` for the current evaluation; checks of the earlier local evaluation are separately labelled.

The second command tests verifier/admission safeguards and rejects corrupted evidence. The third runs the current infrastructure safety suite in a disposable copy. Passing checks confirms the saved evidence and tested controls; it does not change #19924 into a correct decision or repeat fresh model judgement. After editing a manifest-bound document or source file, preserve the previous manifest and refresh the current one before verification.

Do not rerun completed evaluation attempts or GitHub job attempts. Fresh model evaluation requires new owner authorization, a new campaign/freeze and available budget. Opening an eligible issue can invoke hosted inference under the already enabled automatic route; it is not an offline test.

## Stopping the workflow

As the pinned owner, open **Actions → Stop sandbox clarification → Run workflow** on `main`. Inspect disabled ledger flags, preview/approval disablement, cancellation results and unresolved active/pending runs. Disabling alone does not cancel work; provider execution can outlive cancellation. Keep disabled until owner review and do not reset the ledger.

The original stop scanner covers preview/approval executions. If the separate manual evaluator is reenabled, cancel its active run directly in Actions and disable that workflow too. The phone test blocked new model runs, but workflow-disable calls returned HTTP 403. Live cancellation, queue overflow and provider termination remain unverified; DESIGN distinguishes actual tests from simulations.

