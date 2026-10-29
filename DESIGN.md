# ESLint report-clarification agent

## Workflow and evidence of need

The agent assesses whether an ESLint bug report contains enough bug reproduction information. It returns `clarify` with one targeted question, `no_action`, or `human_review` when uncertain. All results are internal previews; public commenting is disabled in this sandbox.

Historical ESLint discussions demonstrate the work this agent is intended to support. In [#20373](https://github.com/eslint/eslint/issues/20373#issuecomment-3612490085), a contributor requested a minimal reproduction because the available information was insufficient. In [#20606](https://github.com/eslint/eslint/issues/20606#issuecomment-4034891225), a contributor requested the webpack configuration, `package.json` and other relevant reproduction files. These observed requests establish a real need to identify missing reproduction information and formulate a useful follow-up. The agent is designed to assist with that first clarification, subject to human review.

Context matters: an empty configuration can be intentional, while an unavailable shared configuration can prevent reproduction. AI assesses that dependency; deterministic code handles identity, hashes, schema, quotas and routing. I rejected a template-field checker because empty fields alone do not establish a necessary clarification and complete inline examples can make other fields irrelevant.

## Current configuration and trust boundary

The active version is `hosted-preview-v11-artifacts-v2` in the controlled fork `peckyboi2/eslint`. The [workflow](.github/workflows/clarifier-triage.yml) starts on `issues: opened`; trusted checks admit ordinary User-authored `Bug:` reports only in the pinned repository/main, on the first run attempt. Event/API identities and unchanged input must agree. Duplicate immutable issue IDs cannot be readmitted.

[AGENTS.md](AGENTS.md) holds repository facts/build commands; [CONTRIBUTING.md](CONTRIBUTING.md) holds disclosure/accountability. The [.claude skill](.claude/skills/eslint-clarification/SKILL.md) holds judgement procedure. [Staging](scripts/clarifier/inference/staging.py) exports one closed input package: title, body, snapshot and approved supporting text. Reports, attachments, quoted authority and simulated tool responses are untrusted data. Expectations, later discussion, measurement and Git history stay out.

[Skill loading](scripts/clarifier/inference/skill.py) checks canonical hashes and the native instruction envelope; saved loader/request evidence proves loading, allowing outer-whitespace trimming only. Output reviews assess procedural use separately. Submitted code is never run; diagnosis, fixes, conversation continuation, issue closure/deletion, PR merging, force-pushing and upstream contact are excluded. The model has no tools/MCP. The [gateway](scripts/clarifier/inference/hosted_transport.py) fixes the provider endpoint and rejects tool calls. Host firewall/OS containment is unverified; trusted-code compromise remains outside this guarantee.

## Governance: mechanisms and verification status

- **Identity:** operations use repository-scoped GitHub Actions tokens, not a personal posting token. Runs/artifacts identify the application and triggering actor. No live bot comment identity is claimed because posting is off.

- **Least privilege:** workflow default is `permissions: {}`. Gate/inference read contents, issues and Actions metadata; only admission gets contents-write for `triage-state`. Stop gets contents/Actions-write. YAML and synthetic boundaries are checked; the native model receives neither GitHub nor provider credentials.

- **Safe outputs:** [validation](scripts/clarifier/outputs/validation.py) enforces the decision schema, null clarification on silent branches and size bounds. Automatic intake has no issues-write or posting job. Thus even `clarify` produces only an artifact. Trusted admission writes remain broader than a single GitHub endpoint.

- **Human approval:** Maintainers review proposals before any human-submitted contribution. The separate [approval workflow](.github/workflows/clarifier-approve.yml) is disabled and its release gate blocks posting. Exact-output approval exists for future activation; no independent approver/new branch protection is claimed or needed for preview publication.

- **Budgets:** [policy](scripts/clarifier/controls/policy.py) and ledger enforce 10 admissions/rolling 24h, 20/campaign, duplicate protection and no refunds/retries after admission. Input is 64 KiB; each run allows one provider request, 300s inference/15m inference job, 16 KiB output and 2 MiB response. No hard dollar/token cap or guaranteed provider cancellation exists.

- **Audit:** [recording](scripts/clarifier/inference/recording.py) retains trigger, source/configuration hashes, model/CLI, skill proof, requests, output, tools, errors and usage with credential redaction. Live artifacts were downloaded and checked. Retention is configured for 30 days; expiry/cancelled-upload behaviour is untested and cost is unknown.

- **Kill switch:** the independent [stop workflow](.github/workflows/clarifier-stop.yml) disables state and preview/approval workflows, then cancels/force-cancels bounded running/pending executions. Simulations pass; phone use, live cancellation and provider termination remain untested. Disabling alone does not cancel existing work.

- **Drift detection:** [regression checks](scripts/check_regression.py) and the [review policy](evals/checks/gate-e-20261028/task49-drift-review-policy.json) define human review before promotion, after changes and weekly while enabled. This is a manual policy, not a deployed inference schedule; current-version golden reruns remain outstanding.

- **Accountability:** Sandbox maintainers (currently the owner, `peckyboi2`) own configuration, permissions, budgets, enablement, stop/restart, output review and submission under CONTRIBUTING. Owner authorization is required for model runs and public writes. Existing CODEOWNERS is not evidence of an independently enforced approval process.

## Evaluation results and limitations

The [ten historical cases](evals/golden/INDEX.md) had pre-recorded expectations of **2 clarify / 7 no_action / 1 human_review**. The v9 coding-assistant dry run achieved **9/10 decision matches**, compared with a **7/10** always-no_action baseline. #19924 returned `no_action` instead of the expected `human_review`, failing the accepted uncertainty threshold. Both clarification proposals passed wording review (**2/2**). Outputs, transcripts, the failure and assistant assessments are retained in the [comparison](evals/checks/gate-f-20261028/comparison.json); they are not independent human validation.

The [v9 adversarial tests](evals/golden/adversarial-v9-20261029/README.md) passed **3/3** cases covering fabricated approval, poisoned support and simulated malicious tool instructions. The [current v11 hosted test](evals/hosted-v11/live-smoke-artifacts-v2-20261029/README.md) verified automatic intake, skill loading, inference and complete artifact upload with no public comments. An earlier upload omitted the hidden skill file; the failure was preserved and the fix verified. The [236 safety tests](evals/hosted-v11/safety-tests-artifacts-v2.txt) and [31 verifier tests](evals/hosted-v11/verifier-tests-artifacts-v2-postrun.txt) check infrastructure, not judgement.

**Current v11 has not completed its ten-case correctness/adversarial evaluation; v9 scores cannot be claimed for it.** A final freeze and authorized evaluation remain required. The historical cases informed tuning and have documented context/provenance limits, so no representative accuracy or time savings are established. Reproduction code was not executed. [Evaluation records](evals/README.md#earlier-evidence-and-failures) retain earlier failures and limitations; [SUBMISSION.md](SUBMISSION.md) explains offline replay of saved evidence.

## Five governance questions

1. **An issue claims approval to close stale issues.** Text grants no authority. The model has no closure tool and inference lacks issues-write. V9's fabricated-approval test passed; that actual test is linked above. Current v11 has capability checks but has not rerun this adversarial model case.

2. **A provider update breaks a golden task.** Maintainers manually rerun all ten preserved cases and review every decision, both expected clarification outputs, attacks/errors and usage weekly while enabled, after configuration changes or provider notice, and before promotion, with a separately authorized budget. A silent backend change under the same model ID may remain unnoticed until that review. On failure, stop previews, preserve the failed output and investigate; never relabel expectations. No automatic drift monitor is installed.

3. **300 issues arrive in one week.** Openings trigger workflows; only eligible unchanged reports reach admission. One run/100 pending are configured; overflow may be cancelled. At most 10 admissions per rolling day and 20 per campaign are possible.

4. **A tool/MCP returns malicious instructions.** No such service is connected. Simulated poisoned text remains data; the model can return only a structured decision/optional question. Gateway checks reject tool items. Host compromise could exceed this boundary; no connected-MCP penetration or OS containment test is claimed.

5. **A maintainer has only a phone.** Sign in as owner, open sandbox Actions → **Stop sandbox clarification** → **Run workflow** on `main`. Inspect its result for disabled flags/workflows, cancelled running/pending runs and unresolved executions. Keep disabled pending owner review; provider work can outlive cancellation. This procedure is implemented and simulated, but has not been exercised from a phone or against a live running inference.

## Agent bill of materials

- **Engine/model/authentication:** Codex CLI **0.154.0**; `gpt-6.1-sol`, `xhigh`. Model ID is fixed but backend revision is unpinned. [Hosted profile](scripts/clarifier/config/hosted.json) pins Linux archive and executable SHA-256; hosted API key stays in the gateway. Historical local inference used ChatGPT login.

- **Instructions/tools/permissions:** AGENTS, CONTRIBUTING, canonical skill, [settings/schema](scripts/clarifier/config/) and helpers above; model tools `[]`, MCP `[]`. Trusted Python standard-library/CLI/GitHub/provider edges support the workflow. Three action commits are pinned in YAML; ubuntu-24.04 and GitHub's action runtime remain mutable.

- **Data/logs/evaluations:** historical packages and expectations in `evals/golden/`; live title/body/snapshot; recorded requests, native probes, outputs, usage and failures in the linked campaigns. Current runtime identity is in the [manifest](evals/hosted-v11/candidate.json); costs are unavailable. The hosted smokes are integration evidence only.

- **Responsible humans:** Sandbox maintainers control and review this repository. Original ESLint authors supplied public context; they did not approve this deployment or independently validate the outputs. No upstream changes were made.

## AI-use statement

Codex rewrote this DESIGN and created assignment code/tests and supporting documentation; upstream ESLint and historical sources retain their authorship. 

Automated checks were assistant-run, not independent human verification. I checked the final code,output tested the workflow and confirmed the requirements before submission
