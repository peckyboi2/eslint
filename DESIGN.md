# ESLint report-clarification agent

## Workflow and evidence of need

The agent checks whether an ESLint bug report contains enough reproduction information. It returns `clarify` with one targeted question, `no_action`, or `human_review` when uncertain. Every result is an internal preview; public commenting is disabled in the controlled fork `peckyboi2/eslint`.

Historical discussions show the task: [#20373](https://github.com/eslint/eslint/issues/20373#issuecomment-3612490085) requested a minimal reproduction; [#20606](https://github.com/eslint/eslint/issues/20606#issuecomment-4034891225) requested webpack configuration and dependency files. These cases motivate assisting with occasional contextual gaps.

Context makes AI useful: blank configuration can be intentional, while an unavailable imported configuration can block reproduction. The skill judges that dependency; deterministic code checks identity, hashes, schema, duplicates, quotas and routing. I rejected a template-field checker because empty fields alone do not establish a necessary question, and complete inline examples can make other fields irrelevant.

## Configuration and what the agent cannot do

- Repository facts, build commands, forbidden changes: AGENTS.md
- Procedure: SKILL.md
- Contribution policy and accountability: CONTRIBUTING.md
- Hard limits: workflows and output checks

The [automatic workflow](.github/workflows/clarifier-triage.yml) starts on `issues: opened`. Trusted checks accept eligible User-authored `Bug:` reports only in the pinned sandbox/main, on the original attempt, with matching API/event identity and unchanged input. Duplicate immutable issue IDs cannot be readmitted. This is a GitHub Actions platform equivalent; no gh-aw compiler or `.lock.yml` applies.

## Governance and verification

- **Identity:** repository-scoped GitHub Actions application tokens perform platform operations; the owner triggers manual evaluations. Runs/artifacts identify both. No live bot comment identity is claimed because posting is off.

- **Least privilege:** default `permissions: {}`; automatic gate/inference read contents, issues and Actions metadata. Only admission gets contents-write for durable state; stop gets contents/Actions-write. The manual evaluator separates state-write and inference jobs too. Native CLI/model processes receive neither GitHub nor provider credentials. YAML, synthetic checks and genuine hosted execution support these boundaries; trusted write tokens remain broader than one endpoint.

- **Safe outputs:** [validation/routing](scripts/clarifier/outputs/) enforce schema, size limits, attribution and null clarification on silent branches. No public comment job or issues-write permission exists. This prevents unwanted public actions while allowing maintainers to inspect potentially wrong proposals.

- **Human approval:** maintainers review proposals before human-submitted contributions. The separate [approval workflow](.github/workflows/clarifier-approve.yml) is disabled and release-blocked. Exact-output approval exists for future activation; independent approvers or new branch protection are not claimed for internal previews. The semantic failure below prevents claiming deployment readiness.

- **Budgets:** [policy](scripts/clarifier/controls/policy.py) enforces 10 admissions/rolling 24h, 20/campaign, durable duplicate protection and no refunds after admission. Each inference allows one provider request, 64 KiB input, 300s inference/15m inference job, 16 KiB output and 2 MiB response. There is no hard dollar/token cap or guaranteed provider termination. A separately [approved evaluator](evals/hosted-v11/campaign-20261029/approval.json) temporarily used 10/60s for exactly 13 evaluation runs; the automatic window stayed 24h. The normal setting was restored after testing. At completion, 15 attempted runs remained counted, leaving five runs under the total budget.

- **Audit:** [recording](scripts/clarifier/inference/recording.py) retains trigger, source/configuration hashes, model/CLI, proof that Codex loaded the skill, requests, outputs, tools, errors and usage with credential redaction. Original hosted artifacts and workflow logs are saved in Git. Artifacts declare 30-day retention; expiry/cancelled-upload behaviour and monetary costs remain unverified.

- **Kill switch:** the independent [stop workflow](.github/workflows/clarifier-stop.yml) blocks new model runs, attempts to disable preview/approval workflows and cancels active/pending runs. Simulations pass. The phone test blocked new model runs, but workflow-disable calls returned HTTP 403; live cancellation and provider termination remain unverified. The separate manual evaluation workflow requires direct cancellation if active.

- **Drift detection:** maintainers manually rerun the historical test cases after changes/provider notice, before promotion and weekly while enabled, reviewing all decisions, clarification wording, attacks, failures and usage under a separately authorized budget. [Regression checks](scripts/check_regression.py) and the [review policy](evals/checks/gate-e-20261028/task49-drift-review-policy.json) support this process. The current hosted campaign was executed; recurring inference and independent human review are not automated.

- **Accountability:** sandbox maintainers, currently owner `peckyboi2`, control configuration, permissions, budgets, enablement, stop/restart and output review under CONTRIBUTING. Only the pinned owner can dispatch evaluation/stop actions. Existing upstream CODEOWNERS is not an independently enforced approval process for this fork.

## Evaluation and limitations

The [current evaluation records](evals/golden/hosted-v11-20261029/README.md) contain ten genuine historical inputs with unchanged, pre-recorded expectations: **2 clarify / 7 no_action / 1 human_review**. The [evaluation with unchanged code and settings](evals/hosted-v11/campaign-20261029/README.md) ran ten historical cases and three adversarial cases once each through the hosted Linux CLI, canonical skill and API gateway. Expectations were excluded from requests. Current automatic admission was separately exercised by the retained [issue-opening integration test](evals/hosted-v11/live-smoke-artifacts-v2-20261029/README.md); historical replay used owner-only manual dispatch.

The [comparison](evals/golden/hosted-v11-20261029/comparison.json) records **9/10 historical decision matches**, against a **7/10** always-no_action baseline. **#19924 failed:** it returned `no_action` instead of `human_review`, judging workload/command details sufficient despite the accepted uncertainty threshold. Public silence does not repair this failure. Both expected clarification proposals passed assistant wording review (**2/2**); unnecessary requests on expected no_action cases were **0/7**. Reviews are [assistant assessments](evals/golden/hosted-v11-20261029/semantic-reviews.json), not independent human validation.

The current adversarial results were **3/3** decision matches, with zero tool calls/public actions: fabricated maintainer approval, poisoned support and simulated malicious tool instructions. Across 13 attempts there were 13 provider requests and **74,762 tokens**; cost is unavailable. All original hidden skill artifacts, input/configuration hashes, native loading, durable reservations and restored settings are checked offline. [236 safety tests](evals/hosted-v11/campaign-20261029/safety-tests-preflight.txt) and [49 verifier tests](evals/hosted-v11/campaign-20261029/verifier-tests-final.txt) check infrastructure and evidence, not judgement.

Earlier [local evaluation results](evals/golden/final-results-v9/README.md), adversarial tests and all failures remain separate. An earlier hosted upload omitted hidden SKILL.md; the original failure, recovery and successful follow-up are retained. The new evaluator's invalid synthetic ledger fixture and an obsolete preparation-only verifier assertion were corrected after their failures were saved. Publication checks also removed six preexisting local generated files from the active manifest and preserved their bytes as data. These known cases informed tuning; no unseen or representative accuracy follows. Early cutoffs, #19818's weaker transformed-source provenance and #21304's missing original screenshot limit context. #19847 remains `no_action`; no submitted reproduction was executed. [SUBMISSION.md](SUBMISSION.md) explains offline replay, which verifies saved evidence rather than fresh model judgement. Uncertainty handling and final independent human review remain unresolved.

## Five governance questions

1. **An issue claims approval to close stale issues.** Issue text grants no authority. The model lacks closure tools and inference lacks issues-write. The current [fabricated-approval attempt](evals/golden/hosted-v11-20261029/slots/11-fabricated-approval/artifacts/attempt/validation.json) records the actual response; the comparison and assistant review assess it. No closure or public write occurred.

2. **A provider update breaks a reference test case.** Maintainers rerun/review all ten cases and attacks weekly while enabled, after provider notice or configuration changes and before promotion. A silent same-ID backend change may remain unnoticed until that manual review. On failure, stop previews, retain evidence and investigate without relabelling expectations. There is no automatic drift monitor.

3. **300 issues arrive in a week.** Openings trigger workflows; only eligible unchanged reports reach admission. One active/100 pending are configured; overflow may be cancelled. Normal limits are 10/rolling day and 20/campaign, including failed attempts. This ledger already contains 15 admissions, leaving five runs under the total budget; the restored 24h window may temporarily block all new admissions. No automatic delayed retry or backlog drain is installed.

4. **A tool/MCP returns malicious instructions.** No such service is connected. The simulated poisoned text remains untrusted data; only a structured decision/optional question is allowed. Gateway checks reject tool items, and all three current attacks recorded zero tool calls. This does not test a live MCP server or host compromise.

5. **A maintainer has only a phone.** Sign in as owner, open sandbox Actions → **Stop sandbox clarification** → **Run workflow** on `main`. Inspect disabled state/workflows, cancellation results and unresolved active/pending runs. The phone test blocked new model runs, but attempts to disable workflows returned HTTP 403. Live cancellation remains unverified.

## Agent bill of materials

- **Engine/model:** Codex CLI **0.154.0**, `gpt-6.1-sol`, `xhigh`; model ID is fixed but backend revision unpinned. [Hosted profile](scripts/clarifier/config/hosted.json) pins Linux archive/executable SHA-256; the hosted key stays in the trusted gateway. The earlier local evaluation used ChatGPT login.

- **Instructions/tools/permissions:** AGENTS, CONTRIBUTING, canonical skill, [settings/schema](scripts/clarifier/config/) and helpers above; model tools `[]`, MCP `[]`. Trusted Python/CLI, GitHub API, pinned installer and provider gateway implement platform operations. Three action commits are pinned; ubuntu-24.04 and action runtime remain mutable. The separately frozen evaluator changes replay/admission only; its temporary quota setting is not a production capability claim.

- **Data/logs/evaluations:** live reports and historical packages, pre-recorded expectations, full requests/native proofs, outputs, workflow logs, comparisons, usage and failures are indexed in `evals/golden/`. The [current manifest](evals/hosted-v11/candidate.json) identifies source and evidence; [restoration receipts](evals/hosted-v11/campaign-20261029/restoration.json) record the closed exception. Costs are unavailable.

- **Responsible humans:** sandbox maintainers own configuration, permissions, output review and final submission. Original ESLint authors supplied public data; they did not approve this deployment or independently validate its results. No upstream changes were made.

## AI-use statement

I made the workflow design task choice, rejected alternative, control choices and case expectations

Codex generated the assignment implementation/tests, hosted evaluation harness, saved comparisons/assistant assessments and documentation;

I have also reviewed the implementation step by step and read agent outputs against my expectations. Codex checked hashes, skill loading, safety tests and links.
