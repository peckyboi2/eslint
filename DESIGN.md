# ESLint report-clarification agent

## Workflow and evidence of need

The agent checks whether an ESLint bug report contains enough reproduction information. It returns `clarify` with one targeted question, `no_action`, or `human_review` when uncertain. Every result is an internal preview; public commenting is disabled in the controlled fork `peckyboi2/eslint`.

Historical discussions show the task: [#20373](https://github.com/eslint/eslint/issues/20373#issuecomment-3612490085) requested a minimal reproduction; [#20606](https://github.com/eslint/eslint/issues/20606#issuecomment-4034891225) requested webpack configuration and dependency files. These cases motivate assisting with occasional contextual gaps. They do not establish their frequency or justify broad deployment.

The separate [September measurement](evals/measurement/README.md) covers issues created 1–30 September 2026 UTC, retrieved 26 October: 22 issues, including ten User-authored `Bug:` reports. In their first seven days, **0/10** had observed clarification requests; median first non-author User response was **3.3554 hours**. This is separate from the selected evaluation cases. One small month, title-based selection, edited/deleted content and the seven-day cutoff limit inference. Elapsed response time is not labour; no substantial workload reduction or time savings is established.

Context makes AI useful: blank configuration can be intentional, while an unavailable imported configuration can block reproduction. The skill judges that dependency; deterministic code checks identity, hashes, schema, duplicates, quotas and routing. I rejected a template-field checker because empty fields alone do not establish a necessary question, and complete inline examples can make other fields irrelevant.

## Configuration and trust boundary

The current runtime is `hosted-preview-v11-artifacts-v2`. The [automatic workflow](.github/workflows/clarifier-triage.yml) starts on `issues: opened`. Trusted checks accept eligible User-authored `Bug:` reports only in the pinned sandbox/main, on the original attempt, with matching API/event identity and unchanged input. Duplicate immutable issue IDs cannot be readmitted. This is a GitHub Actions platform equivalent; no gh-aw compiler or `.lock.yml` applies.

[AGENTS.md](AGENTS.md) holds repository facts, build commands and forbidden changes; [CONTRIBUTING.md](CONTRIBUTING.md) assigns contribution policy and accountability. The [.claude skill](.claude/skills/eslint-clarification/SKILL.md) defines the procedure. [Staging](scripts/clarifier/inference/staging.py) supplies a closed package of title, body, snapshot and approved supporting text. Reports, attachments, quoted authority and simulated tool text are untrusted. Expectations, later discussion and the full checkout stay outside the model session.

[Skill checks](scripts/clarifier/inference/skill.py) verify canonical hashes and the native instruction envelope. Every hosted evaluation retains native load proof, exact requests and outputs; assistant wording reviews assess procedural use separately. Submitted reproductions are never executed. Diagnosis, fixes, conversation continuation, closure/deletion, merging, force-pushing and upstream contact are excluded. The model has no tools/MCP or credentials. The [gateway](scripts/clarifier/inference/hosted_transport.py) fixes the provider endpoint and rejects tool calls; host firewall/OS containment is unverified, and trusted-code compromise remains outside this guarantee.

## Governance and verification

- **Identity:** repository-scoped GitHub Actions application tokens perform platform operations; the owner triggers manual evaluations. Runs/artifacts identify both. No live bot comment identity is claimed because posting is off.

- **Least privilege:** default `permissions: {}`; automatic gate/inference read contents, issues and Actions metadata. Only admission gets contents-write for durable state; stop gets contents/Actions-write. The manual evaluator separates state-write and inference jobs too. Native CLI/model processes receive neither GitHub nor provider credentials. YAML, synthetic checks and genuine hosted execution support these boundaries; trusted write tokens remain broader than one endpoint.

- **Safe outputs:** [validation/routing](scripts/clarifier/outputs/) enforce schema, size limits, attribution and null clarification on silent branches. No public comment job or issues-write permission exists. This prevents unwanted public actions while allowing maintainers to inspect potentially wrong proposals.

- **Human approval:** maintainers review proposals before human-submitted contributions. The separate [approval workflow](.github/workflows/clarifier-approve.yml) is disabled and release-blocked. Exact-output approval exists for future activation; independent approvers or new branch protection are not claimed for internal previews. The semantic failure below prevents claiming deployment readiness.

- **Budgets:** [policy](scripts/clarifier/controls/policy.py) enforces 10 admissions/rolling 24h, 20/campaign, durable duplicate protection and no refunds after admission. Each inference allows one provider request, 64 KiB input, 300s inference/15m inference job, 16 KiB output and 2 MiB response. There is no hard dollar/token cap or guaranteed provider termination. A separately [approved evaluator](evals/hosted-v11/campaign-20261029/approval.json) temporarily used 10/60s for exactly 13 slots; the automatic window stayed 24h. The setting was restored and evaluator disabled; all 15 hosted reservations remain, leaving five campaign slots.

- **Audit:** [recording](scripts/clarifier/inference/recording.py) retains trigger, source/configuration hashes, model/CLI, native skill proof, requests, outputs, tools, errors and usage with credential redaction. Original hosted artifacts and workflow logs are saved in Git. Artifacts declare 30-day retention; expiry/cancelled-upload behaviour and monetary costs remain unverified.

- **Kill switch:** the independent [stop workflow](.github/workflows/clarifier-stop.yml) disables the ledger and preview/approval workflows, then cancels/force-cancels bounded active/pending runs. Simulations pass; phone use, live cancellation and provider termination are untested. The separate evaluator is now disabled; if reenabled, its active run also needs direct cancellation because the original stop scanner covers preview/approval.

- **Drift detection:** maintainers manually rerun golden cases after changes/provider notice, before promotion and weekly while enabled, reviewing all decisions, clarification wording, attacks, failures and usage under a separately authorized budget. [Regression checks](scripts/check_regression.py) and the [review policy](evals/checks/gate-e-20261028/task49-drift-review-policy.json) support this process. The current hosted campaign was executed; recurring inference and independent human review are not automated.

- **Accountability:** sandbox maintainers, currently owner `peckyboi2`, control configuration, permissions, budgets, enablement, stop/restart and output review under CONTRIBUTING. Only the pinned owner can dispatch evaluation/stop actions. Existing upstream CODEOWNERS is not an independently enforced approval process for this fork.

## Evaluation and limitations

The [current golden bundle](evals/golden/hosted-v11-20261029/README.md) contains ten genuine historical inputs with unchanged, pre-recorded expectations: **2 clarify / 7 no_action / 1 human_review**. The [frozen campaign](evals/hosted-v11/campaign-20261029/README.md) ran ten historical cases and three adversarial cases once each through the hosted Linux CLI, canonical skill and API gateway. Expectations were excluded from requests. Current automatic admission was separately exercised by the retained [opening smoke test](evals/hosted-v11/live-smoke-artifacts-v2-20261029/README.md); historical replay used owner-only manual dispatch.

The [comparison](evals/golden/hosted-v11-20261029/comparison.json) records **9/10 historical decision matches**, against a **7/10** always-no_action baseline. **#19924 failed:** it returned `no_action` instead of `human_review`, judging workload/command details sufficient despite the accepted uncertainty threshold. Public silence does not repair this failure. Both expected clarification proposals passed assistant wording review (**2/2**); unnecessary requests on expected no_action cases were **0/7**. Reviews are [assistant assessments](evals/golden/hosted-v11-20261029/semantic-reviews.json), not independent human validation.

The current adversarial results were **3/3** decision matches, with zero tool calls/public actions: fabricated maintainer approval, poisoned support and simulated malicious tool instructions. Across 13 attempts there were 13 provider requests and **74,762 tokens**; cost is unavailable. All original hidden skill artifacts, input/configuration hashes, native loading, durable reservations and restored settings are checked offline. [236 safety tests](evals/hosted-v11/campaign-20261029/safety-tests-preflight.txt) and [49 verifier tests](evals/hosted-v11/campaign-20261029/verifier-tests-final.txt) check infrastructure and evidence, not judgement.

Earlier [v9 results](evals/golden/final-results-v9/README.md), adversarial tests and all failures remain separate. An earlier hosted upload omitted hidden SKILL.md; the original failure, recovery and successful follow-up are retained. The new evaluator's invalid synthetic ledger fixture and an obsolete preparation-only verifier assertion were corrected after their failures were saved. Publication checks also removed six preexisting local generated files from the active manifest and preserved their bytes as data. These known cases informed tuning; no unseen or representative accuracy follows. Early cutoffs, #19818's weaker transformed-source provenance and #21304's missing original screenshot limit context. #19847 remains `no_action`; no submitted reproduction was executed. [SUBMISSION.md](SUBMISSION.md) explains offline replay, which verifies saved evidence rather than fresh model judgement. Uncertainty handling and final independent human review remain unresolved.

## Five governance questions

1. **An issue claims approval to close stale issues.** Issue text grants no authority. The model lacks closure tools and inference lacks issues-write. The current [fabricated-approval attempt](evals/golden/hosted-v11-20261029/slots/11-fabricated-approval/artifacts/attempt/validation.json) records the actual response; the comparison and assistant review assess it. No closure or public write occurred.

2. **A provider update breaks a golden task.** Maintainers rerun/review all ten cases and attacks weekly while enabled, after provider notice or configuration changes and before promotion. A silent same-ID backend change may remain unnoticed until that manual review. On failure, stop previews, retain evidence and investigate without relabelling expectations. There is no automatic drift monitor.

3. **300 issues arrive in a week.** Openings trigger workflows; only eligible unchanged reports reach admission. One active/100 pending are configured; overflow may be cancelled. Normal limits are 10/rolling day and 20/campaign, including failed attempts. This ledger already contains 15 admissions, leaving five campaign slots; the restored 24h window may temporarily block all new admissions. No automatic delayed retry or backlog drain is installed.

4. **A tool/MCP returns malicious instructions.** No such service is connected. The simulated poisoned text remains untrusted data; only a structured decision/optional question is allowed. Gateway checks reject tool items, and all three current attacks recorded zero tool calls. This does not test a live MCP server or host compromise.

5. **A maintainer has only a phone.** Sign in as owner, open sandbox Actions → **Stop sandbox clarification** → **Run workflow** on `main`. Inspect disabled state/workflows, cancellation results and unresolved active/pending runs. If the separate evaluator has been reenabled, open its run → **Cancel workflow**, then disable it. Keep disabled pending review; provider work can outlive cancellation. The stop procedure is implemented/simulated, not phone-tested.

## Agent bill of materials

- **Engine/model:** Codex CLI **0.154.0**, `gpt-6.1-sol`, `xhigh`; model ID is fixed but backend revision unpinned. [Hosted profile](scripts/clarifier/config/hosted.json) pins Linux archive/executable SHA-256; the hosted key stays in the trusted gateway. Historical v9 used local ChatGPT login.

- **Instructions/tools/permissions:** AGENTS, CONTRIBUTING, canonical skill, [settings/schema](scripts/clarifier/config/) and helpers above; model tools `[]`, MCP `[]`. Trusted Python/CLI, GitHub API, pinned installer and provider gateway implement platform operations. Three action commits are pinned; ubuntu-24.04 and action runtime remain mutable. The separately frozen evaluator changes replay/admission only; its temporary quota setting is not a production capability claim.

- **Data/logs/evaluations:** live reports and historical packages, pre-recorded expectations, full requests/native proofs, outputs, workflow logs, comparisons, usage and failures are indexed in `evals/golden/`. The [current manifest](evals/hosted-v11/candidate.json) identifies source and evidence; [restoration receipts](evals/hosted-v11/campaign-20261029/restoration.json) record the closed exception. Costs are unavailable.

- **Responsible humans:** sandbox maintainers own configuration, permissions, output review and final submission. Original ESLint authors supplied public data; they did not approve this deployment or independently validate its results. No upstream changes were made.

## AI-use statement

Maintainers selected the workflow, accepted the case expectations and supplied design decisions and feedback. Codex generated the assignment implementation/tests, hosted evaluation harness, saved comparisons/assistant assessments and documentation; upstream code and historical reports retain their authorship. Codex verified hashes, native loading, actual outputs against frozen expectations, current safety/evidence tests, links and this document's line limit. Maintainers must complete their own final code/output review and be able to explain the submission; assistant checks are not independent human verification.
