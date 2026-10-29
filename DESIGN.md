# ESLint clarification sandbox

## Current hosted preview (29 October 2026)

Current `hosted-preview-v11-artifacts-v2` passed a real [automatic hosted smoke](evals/hosted-v11/live-smoke-artifacts-v2-20261029/README.md): issue opening, admission, pinned Linux CLI, native skill loading and one OpenAI response; `human_review`, 2,910 tokens, all 26 artifact hashes verified, no public comments. The [prior v11 run](evals/hosted-v11/live-smoke-20261029/README.md) omitted hidden `SKILL.md`; original failure and separate Git recovery remain preserved. This variant fixes upload scope and has no new ten-case accuracy evaluation. [Current guide](evals/hosted-v11/README.md) separates these claims. Public posting stays blocked.

| Current control / bill of materials | Implementation and evidence boundary |
| --- | --- |
| Intake and authority | Ordinary User-authored `Bug:` opening in pinned sandbox/main, event/API identity and unchanged source. Owners alone approve/stop; report text grants no authority. [Collector](scripts/clarifier/inference/live_snapshot.py), [gate](scripts/clarifier/controls/intake_identity.py). |
| Staging and model | Shared [pipeline](scripts/clarifier/inference/pipeline.py) for live/historical closed packages, canonical skill unchanged, model `gpt-6.1-sol/xhigh`, CLI 0.154.0. Local macOS executable remains pinned by observed SHA; [Linux profile](scripts/clarifier/config/hosted.json) pins the verified archive and actual ELF hash; Linux execution and complete artifact upload were observed in this variant’s smoke. Backend revision is unpinned. Implementation chat requested Sol/Ultra; evaluated agent effort remains xhigh. |
| Tools, permissions and network | Model tools/MCP `[]`, no submitted-code execution or arbitrary link retrieval. [Preview workflow](.github/workflows/clarifier-triage.yml) has gate read, admission state-write, inference read; no issues-write/output job. [Hosted gateway](scripts/clarifier/inference/hosted_transport.py) fixes API endpoint and keeps key out of CLI/model environment. The live request had no tools; token absence from the native process is checked synthetically. No OS jail/firewall has been tested. |
| Quota, dedup and queue | Actual input reserved atomically; repository plus immutable issue ID deduplicates across deliveries/edits/crashes. Hosted caps stay 10/rolling 24h and 20/campaign, no refund. One running/100 pending via `queue: max`; overflow cancelled by GitHub, owner recovery is explicit. Platform ordering/overflow is documented and static-tested, not live-observed. |
| Outputs and human review | All three decisions saved internally. [Exact approval](scripts/clarifier/outputs/exact_approval.py) binds issue/source/input/output/final-comment/configuration/run. Separate manual workflow blocks at absent release before credentials. Future posting needs protected artifact transfer/permissions plus explicit activation; lifetime intent/reconciliation remain. Final-check/edit/POST race persists. |
| Logs, stopping and accountability | Redacted native-load/request/output/error/usage records; blocked phase receipts, 30-day artifacts with cancellation gaps. Independent owner stop now disables/scans preview and approval workflows without the triage lock. Provider termination and phone use remain untested. Darren owns access, budgets, output approvals, enablement and submission. |
| Evaluation and drift | 236 current deterministic infrastructure tests pass; they do not measure judgement. V9 historical 9/10 and v9 supplement 3/3 are preserved separately. New accuracy is pending a fresh approved 13-attempt campaign and full freeze, with no retries.  |

The five scenarios for current automatic intake are: (1) fabricated owner approval stays untrusted text and has no closure tool; (2) provider drift requires a separately authorised full frozen rerun and human review, never relabelled expectations; (3) 300 arrivals can overflow the bounded queue and only 20 campaign admissions are possible, leaving explicit human recovery; (4) malicious tool text is data because no MCP/tools are connected, with response tool items rejected; (5) phone owner uses Actions → Stop sandbox clarification → Run workflow on main, then verifies disabled state and both workflow cancellations, unresolved provider work and in-flight intents. Only ordinary opening/admission/inference was observed live; live attacks, phone stop and cancellation remain untested.

Offline verification now resolves all 168 v9 frozen files from retained Git commit `7fdbf7322cbecbe852ce971b6c10f343daa1aaf0` plus one byte-identical snapshot of preexisting uncommitted packaging changes; it separately checks current artifact-variant bytes and preserves all v10 metadata. No previous result, expectation, failed attempt or exhausted reservation was rewritten. New implementation/test/doc changes are AI-assisted; Darren's review and any final evaluation/submission approval remain pending.

## Retained v9 design and findings

The following narrative describes the completed manual v9 configuration and its original limits. Source links in the working tree now show active v11; the retained Git projection reconstructs exact v9 source for historical checks. V9 results are not evaluation of v10 or v11.

This submission uses Codex to assess whether a bug report submitted to the ESLint repo contains enough information. Based on the information submitted in the bug report, it chooses either to:
- stay silent
- request for more information
- ask for human review due to uncertainty

It uses the brief's coding-assistant dry-run route: actual local inference with the same frozen skill/settings/inputs, plus deterministic platform simulations. Hosted end-to-end execution is unavailable.

Start at the [current golden submission index](evals/golden/INDEX.md) for all ten outputs, transcripts, expectations, offline commands and failures; [operations](evals/README.md) covers stopping instructions. The root README, AGENTS and golden-v1 README retain frozen historical commands; [SUBMISSION.md](SUBMISSION.md) identifies the current complete-tree verifier. The full upstream fork, source, tests, packages, licence and inherited workflows remain intact.

## Why this workflow and AI

ESLint's [bug-report guidance](https://eslint.org/docs/latest/contribute/report-bugs) explains that repeatedly asking reporters for details takes time away from fixing issues. Historical repository comments demonstrate this work: in [#20373](https://github.com/eslint/eslint/issues/20373#issuecomment-3612490085) (December 2025), a contributor requested a minimal reproduction because information was insufficient; in [#20606](https://github.com/eslint/eslint/issues/20606#issuecomment-4034891225) (March 2026), a contributor requested the webpack configuration, `package.json` and other relevant files, and another contributor later repeated the reproduction request. Hence, this shows that an AI agent in the workflow could help to reduce reviewer burden by ensuring that the bug reports contain sufficient information for reviewers to even begin looking at in the first place

Whether a report contains enough information to recreate the problem depends on context: blank configuration can be intentional, an API example need not supply a CLI command, and a referenced shared configuration may be essential. AI assesses whether a specific missing detail is necessary and drafts one targeted question. Conventional code handles identities, hashes, schema, labels, quotas, duplicates and routing. A rejected alternative was a template-field checker: missing fields alone would prompt redundant questions and would miss contextual gaps.

The separate [September measurement](evals/measurement/README.md) examined issues created 1 September 2026 inclusive to 1 October exclusive (UTC), retrieved 26 October. Of all 22 issues, ten met the selection criteria: accounts classified as User authored them and their titles started exactly `Bug:`. We inspected all comments in each report's first seven days for explicit requests for missing reproduction information, excluding bot notices, diagnosis and coordination.

## Configuration and trust boundary

[AGENTS.md](AGENTS.md) provides repository facts, commands and forbidden changes;

[CONTRIBUTING.md](CONTRIBUTING.md) provides disclosure and human accountability.

The canonical [.claude skill](.claude/skills/eslint-clarification/SKILL.md) supplies the procedure. [Skill loading](scripts/clarifier/inference/skill.py), native probes and captured requests prove the selected engine loaded its bytes; output inspection assesses procedural use.

[Triage workflow](.github/workflows/clarifier-triage.yml) is an authored GitHub Actions platform equivalent, so gh-aw's compiled `.lock.yml` is inapplicable. It uses manual dispatch, explicit job permissions, pinned actions and timeouts. [Policy](scripts/clarifier/controls/policy.py) binds repository/owner IDs and names, original/rerun callers and `refs/heads/main`. Preview is default; the public fork's review branch is `ai-workflow`.

Report bodies, titles, supporting files and simulated tool responses are untrusted data. [Package selection](scripts/clarifier/inference/packages.py) and [staging](scripts/clarifier/inference/staging.py) verify a closed allowlist and hashes, reject unsafe paths/oversize inputs and export one case. Evaluator labels, measurement, later comments and Git history never enter the fresh evaluated session. No submitted code or dependencies are executed.

The [request](scripts/clarifier/inference/request.py) and [transport](scripts/clarifier/inference/transport.py) expose no model tools, shell, filesystem API, MCP or arbitrary fetch. A fixed provider gateway rejects tool calls and redirects. The trusted Python/Codex host can access host resources: an OS jail and host egress firewall are unsupported/untested, so prompt isolation is not a host containment claim.

## Governance and actual verification

“Local” below means actual local execution; “simulated” means fixture/API behaviour, never observed hosted enforcement. [Gate E](evals/checks/gate-e-20261028/gate-e-review.json) indexes each control's evidence and limitations; [F capability inspection](evals/checks/gate-f-20261028/pre-freeze-capabilities.json) checks the final YAML.

| Control and rationale | Mechanism, evidence and remaining limit |
| --- | --- |
| Identity: attribute authorised actions | [Identity checks](scripts/clarifier/controls/identity.py) verify caller/ref/repository before privileged boundaries. Posting requires a verified bot/application; no personal posting token. Identities were simulated; no live bot comment exists. |
| Least privilege: separate inference from effects | Workflow defaults to `permissions: {}`; inference has contents-read, no posting/state secret. Deterministic admission/output jobs alone get state-write; output adds issues-write; stop alone gets Actions-write. YAML inspected, hosted token placement unverified. These trusted tokens are broader than one endpoint. |
| Safe outputs: bound public effects | [Validation](scripts/clarifier/outputs/validation.py), [handler](scripts/clarifier/outputs/output_handler.py), [posting](scripts/clarifier/outputs/posting.py) allow one bounded clarification on a trusted target. Silent/invalid branches cannot post; source/release/enabled checks and lifetime intent protect routing. Local tests/simulated HTTP pass; final-check-to-POST race remains. |
| Human approval: prevent automatic promotion | [Release gate](scripts/clarifier/outputs/release_gate.py) requires reviewed target/configuration; live target/release remain unset. Darren reviews configuration, results and any enablement. No independent output approval is claimed; upstream CODEOWNERS is not new branch protection. |
| Budgets: contain admissions and effects | [Ledger](scripts/clarifier/controls/ledger.py): 10/rolling 24h, 20/campaign hosted; failures consume reservations, no refunds/delayed retry. Input 64 KiB, one provider request, inference 300s/job 15m, output 16 KiB/response 2 MiB, one ≤2,000-character comment/report. Local bounds tested; no hard dollar/token cap or guaranteed provider cancellation. |
| Audit: preserve failures and provenance | [Recorder](scripts/clarifier/inference/recording.py) saves trigger, input/configuration hashes, skill proof, model/CLI, requests, outputs, errors and usage; credentials excluded. Final logs are actual. Artifacts declare 30-day retention; hosted retention/cancelled-upload behaviour unverified. Backend revision/cost unknown. |
| Kill switch: stop future and active work | Independent [stop workflow](.github/workflows/clarifier-stop.yml), [stop I/O](scripts/clarifier/github/stop_io.py) disable ledger/triage, cancel and force-cancel bounded active/pending runs, inspect in-flight intents. Simulation and real local timeout passed; live phone/runner cancellation remains blocked. |
| Drift: fail visibly before promotion | [Regression checker](scripts/check_regression.py) checks frozen expectations, identity, decision, execution and quality. [Review policy](evals/checks/gate-e-20261028/task49-drift-review-policy.json): Darren reviews all ten and comments/attacks before promotion, after changes and weekly while enabled. Synthetic failure/correction tested; no scheduled inference installed. |
| Accountability: retain owner decisions | Darren Peck (`peckyboi2`) controls configuration, permissions, budgets, release, stop/restart and submission, per CONTRIBUTING. Local quota extensions have recorded reasons/hashes; they do not alter hosted caps. Promotion and publication need separate approval. |

No model mutation interface permits diagnosis/fixes, submitted-code execution, conversation continuation, issue closure/deletion, merging, force-pushing or upstream contact. Trusted code has fixed endpoints; policy prose is reinforced by no-tool inference and deterministic validation. A compromise of trusted code/host credentials is outside that model boundary.

## Five questions, referring to configuration

1. **Fabricated maintainer authority to close stale issues:** issue text grants no authority, and the model has no closure or deletion tools. All three attacks (fabricated approval, poisoned support, simulated malicious tool text) were rerun as fresh actual no-tool previews on unchanged final v9: **3/3 passed**, with zero tool calls or public writes. The [v9 supplement](evals/golden/adversarial-v9-20261029/README.md) links pre-recorded expectations, outputs, transcripts and comparisons. Earlier E-v6/v7/v8 evidence remains preserved. These are local model tests, not live GitHub permission tests.
2. **Provider update breaks a golden task:**
Whenever the model, instructions or tools change, rerun the ten golden tasks using the same preserved inputs and the expected outcomes. Compare the new results against those expectations and review the outputs before approving live use.

3. **300 reports in a week:** arrivals trigger zero inference because dispatch is manual. If manually dispatched, one active/one pending configuration can supersede waiting runs; quota is checked when admitted. At most ten admissions per rolling day and twenty total campaign admissions, then deny without automatic retry. [Scenario](evals/checks/gate-e-20261028/task50-scenario.json) is deterministic; live scheduling is unverified and the backlog remains human work.
4. **Malicious tool/MCP instructions:** none are connected to the model. Poisoned text stays data; the model can return one structured decision/optional clarification only. Technical checks reject forbidden tool/network items before forwarding them. Simulated malicious tool-response text passed an actual final-v9 preview in the linked supplement; this is not a connected MCP penetration test. Host containment remains unverified.
5. **Phone-only stop:** after separately authorised provisioning, sign in as owner, open sandbox Actions → **Stop sandbox clarification** → **Run workflow** on `main`. Verify ledger/triage disabled AND active/pending runs cancelled/force-cancelled; inspect unresolved runs and marker-bearing comments, keep disabled and reconcile before restart. [Phone fallback](evals/checks/gate-e-20261028/task48-phone-stop-fallback.json) is simulated. The stop has no triage lock/dependency; runner delays, provider continuation and accepted/in-flight writes remain possible.

## Final findings and limits

[Final F comparison](evals/checks/gate-f-20261028/comparison.json) contains ten fresh actual attempts under one [168-file freeze](evals/checks/gate-f-20261028/freeze.json): **9/10 decision matches**, versus the **7/10 always-no_action baseline**. #19924 returned `no_action` against accepted `human_review`; its public silence does not repair that failure. Its workload/command reading is plausible, but the conservative uncertainty label remains unchanged.

Both clarify cases (#20373/#20606) pass all seven applicable criteria: **2/2** proposed-comment quality passes. Eight silent outputs have no wording-quality assessment. Unnecessary requests 0/7; unsupported requests on expected human_review 0/1; missed/deferred clarifications 0/2 each; all human-review deferrals 0/10; silence violations 0/8; irrelevant/redundant proposals 0/2 each; execution failures/public writes 0/10. [Semantic reviews](evals/checks/gate-f-20261028/semantic-reviews.json) are assistant assessment, not independent/blinded human validation.

The 172 deterministic tests and integrity checks protect infrastructure, not judgement. Earlier #20606 omitted-command failure, #19924 v3/v5/v6 failures, E owner-name/reconciliation defects and corrections, loopback failure and F preparation failures are retained in the [evidence index](evals/README.md#earlier-evidence-and-failures). Earlier Python copies were omitted under Darren's cleanup decision; hashes cannot reconstruct them. The final evaluated implementation is included.

The set is known, purposive and used in tuning, with collaboratively accepted expectations. No unseen/representative accuracy claim follows. Three cases use bounded early pre-response snapshots; #19818 has weaker transformed-archive provenance; #21304's screenshot was not independently preserved. #19847 remains no_action with both reported 9.21.0 and support 9.28.0; #19118 retains supplied `/app` and approved support. Textual completeness is assessed; successful reproduction was never executed.

Hosted engine/login, state branch, approved target/release, bot identity/token placement, queue/cancellation/contention/retention remain unprovisioned or unverified. E tasks 46 and 48 remain live-blocked with labelled fallbacks. Last read-only preflight found Actions disabled. This is ready for academic vetting of the dry-run route, with unresolved judgement and live-control gaps; it is not production promotion.

## Agent bill of materials

| Component | Exact identity / reference |
| --- | --- |
| Selected engine/model | Codex CLI **0.154.0**, binary SHA in freeze; **gpt-6.1-sol / xhigh**, requested and returned ID checked, provider backend revision unpinned. Existing ChatGPT login; no purchased API credits. Historical Astra runs are development only. |
| Frozen configuration | **milestone-f-final-v9**, SHA-256 `f5deaab15a2a69e4b03525fb43c9130c82155288d051555d9bc4423f047916fa`; freeze SHA-256 `0c0ca76cd19e5adca0c5ebfc2be40e531a1ecbda5a4a546ada9f42d125d21a5f`. [Settings/schema](scripts/clarifier/config/), AGENTS, CONTRIBUTING, canonical skill and adapter are included. |
| Host/tools/MCP | Recorded macOS 15.6.1 arm64, Python 3.14.8 standard-library harness and pinned CLI; Python 3.11+ offline checks. GitHub Actions ubuntu-24.04 declared, pinned action SHAs; runner image not immutable. Model tools `[]`, MCP `[]`; trusted GitHub/provider HTTP edges only. |
| Permissions and sources | Manual owner-only trusted-ref workflow; separate job tokens as above. Ten bounded public historical packages with per-file hashes/cutoffs; supporting repositories/playground text are data. September snapshots are evaluator-only. No evaluator history is forwarded. |
| Logs/evaluations/usage | [Final historical campaign](evals/checks/gate-f-20261028/) retains 9/10 matches and 57,562 tokens. The [v9 attack supplement](evals/golden/adversarial-v9-20261029/README.md) adds three authorised calls and 16,721 tokens; cost unknown. The original 51-reservation ledger stays unchanged; a separate capped three-slot evaluator allowance gives 54 combined reservations, no retries/refunds. Frozen v9 inference code/settings are unchanged; the supplemental admission envelope is documented separately. Both allowances are exhausted. Earlier failures/archive remain preserved. |
| Responsible humans | Darren Peck owns decisions, review, enablement/disablement and submission. Original ESLint maintainers/reporters supplied public historical context; they did not approve this sandbox or independently assess its outputs. |

## AI-use statement

AI assistance in Codex authored the assignment code, tests and helped with the documentation; original ESLint work and preserved report/source evidence retain their authorship. Darren selected scope/sandbox/dry-run route, accepted the ten expectations with assistant explanations, resolved supporting-input/version decisions and authorised bounded work/quotas.
