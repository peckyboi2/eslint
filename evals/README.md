# Evaluation, reproduction and operations

Start with [DESIGN.md](../DESIGN.md). This is the current evaluation home for the marker; all instructions use this repository alone. The root README and [golden README](golden/README.md) retain their frozen historical wording. Actual outputs/logs live beside the immutable `golden/` inventory and are indexed here rather than added to golden-v1.

## Final campaign and evidence

`final-f-20261028-v9` is the only final comparison: ten fresh actual coding-assistant previews, one predeclared attempt each, no retries or earlier-answer substitutions. Configuration `milestone-f-final-v9` has SHA-256 `f5deaab15a2a69e4b03525fb43c9130c82155288d051555d9bc4423f047916fa`; the [168-file freeze](checks/gate-f-20261028/freeze.json) has SHA-256 `0c0ca76cd19e5adca0c5ebfc2be40e531a1ecbda5a4a546ada9f42d125d21a5f`.

| Evidence | Location and interpretation |
| --- | --- |
| Historical inputs and provenance | [prepared packages](golden/prepared-inputs/), [manifest](golden/prepared-inputs/manifest.json), per-case `snapshot.json`, original hash inventory and [golden freeze](golden/FREEZE.json). Do not execute supplied code. |
| Predeclared expectations | [expectations](golden/expectations.json), [accepted reasons](golden/expected-decision-review.md), [quality criteria](golden/comment-quality.md), [plan](golden/evaluation-plan.md). Evaluator-only, excluded from inference. |
| Final results | [comparison](checks/gate-f-20261028/comparison.json), [semantic reviews](checks/gate-f-20261028/semantic-reviews.json), [Gate F review](checks/gate-f-20261028/gate-f-review.json). Reviews are assistant assessments after output, not Darren's independent/blinded approval. |
| Final integrity and usage | [integrity/quota](checks/gate-f-20261028/final-integrity-quota.json), ten before/after boundary records, [deterministic tests](checks/gate-f-20261028/pre-freeze-tests-v3.txt), [capabilities](checks/gate-f-20261028/pre-freeze-capabilities.json). Infrastructure success is separate from judgement. |
| Required packaging | [F evidence list](checks/gate-f-20261028/required-evidence-for-g.json); its “G unstarted” status is historical. All final runs, control records and earlier attempts are retained in this candidate. |
| Separate need measurement | [September cohort](measurement/README.md), fixed public-source snapshots, coding, CSV, summary and hashes. This is not the final agent evaluation. |

| Case | Expected → actual | Raw output | Per-case review |
| --- | --- | --- | --- |
| #20373 | clarify → clarify | [output](runs/final-f-20261028-v9-01-20373-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/20373.json) |
| #20606 | clarify → clarify | [output](runs/final-f-20261028-v9-02-20606-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/20606.json) |
| #19924 | human_review → no_action | [output](runs/final-f-20261028-v9-03-19924-a1/raw-output.txt) | [FAIL](checks/gate-f-20261028/comparisons/19924.json) |
| #19044 | no_action → no_action | [output](runs/final-f-20261028-v9-04-19044-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/19044.json) |
| #21320 | no_action → no_action | [output](runs/final-f-20261028-v9-05-21320-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/21320.json) |
| #19477 | no_action → no_action | [output](runs/final-f-20261028-v9-06-19477-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/19477.json) |
| #21304 | no_action → no_action | [output](runs/final-f-20261028-v9-07-21304-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/21304.json) |
| #19847 | no_action → no_action | [output](runs/final-f-20261028-v9-08-19847-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/19847.json) |
| #19118 | no_action → no_action | [output](runs/final-f-20261028-v9-09-19118-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/19118.json) |
| #19818 | no_action → no_action | [output](runs/final-f-20261028-v9-10-19818-a1/raw-output.txt) | [pass](checks/gate-f-20261028/comparisons/19818.json) |

Decision matches are 9/10 versus an always-`no_action` baseline of 7/10. Both clarification proposals pass all seven applicable criteria (2/2); eight silent outputs have no wording-quality assessment. Unnecessary requests are 0/7, unsupported requests on expected `human_review` 0/1, missed/deferred clarifications 0/2 each, all deferrals 0/10, silence violations 0/8, irrelevant/redundant comments 0/2 each, execution failures/public writes 0/10. #19924's public silence does not make its internal classification correct.

The #19924 rationale accepts the command, workload size and stack trace as sufficient. The accepted conservative expectation requires internal uncertainty because no reproducible workload is established and no particular absent detail is established as necessary. A competing `no_action` reading is plausible; this remains a failed match without relabelling. These known purposive development/regression cases were used during tuning, so neither generalisation nor production readiness follows. No workload/time savings were measured.

## Inspect an actual run

Each linked run directory retains `record.json`, `artifact-hashes.json`, `configuration-hashes.json`, retained `configuration/` skill/settings/schema, `input/`, `input-manifest.json`, `loader.json`, `native-load-probe.json`, `request.json`, `raw-output.txt`, `transcript.jsonl` and `validation.json` (see the exact inventory for that attempt). The request records only the canonical skill and one approved case, `tools=[]`, `tool_choice=none` and no conversation history. Loader/native-prompt records and procedural output provide skill-use evidence; an unsupported model claim is not the proof.

The record identifies requested/returned model, pinned engine binary, settings, errors, usage and empty tool/public-action lists. F used `gpt-6.1-sol`/`xhigh`, Codex CLI `0.154.0`, existing ChatGPT login, and 57,562 recorded tokens. Backend revision and monetary cost are unknown. Historical Astra answers retain their original identities and do not enter the final score. Private temporary homes and login credentials are excluded; saved absolute paths describe the original host and are not dependencies.

## Offline reproduction: no inference or network

Use Python 3.11+ and the standard library from the repository root. No Node installation or submitted dependency installation is needed. Run the existing safety suite:

```sh
python3 -B -m unittest discover -s scripts/clarifier/tests -t scripts -p 'test_*.py' -v
git diff --check
```

Stage every approved case into a disposable directory using the same trusted helpers, inspect the closed inventories, and reproduce the comparison without overwriting evidence:

```sh
PYTHONPATH=scripts python3 -B - <<'PY'
import hashlib, json, tempfile
from pathlib import Path
from clarifier.inference import packages, staging
from clarifier.outputs import campaign, campaign_metrics

root = Path.cwd().resolve()
folder = root / 'evals/checks/gate-f-20261028'
raw = (folder / 'freeze.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == '0c0ca76cd19e5adca0c5ebfc2be40e531a1ecbda5a4a546ada9f42d125d21a5f'
frozen = json.loads(raw)
campaign.verify_files(root, frozen['files'])
with tempfile.TemporaryDirectory(prefix='clarifier-offline-') as name:
    for row in frozen['cases']:
        package = packages.load(row['issue'], root)
        manifest = staging.stage(package.source, Path(name) / str(row['issue']), expected=package.hashes)
        assert manifest['source_hashes'] == row['input_hashes']
expected = {row['issue']: row['decision'] for row in json.loads((root / 'evals/golden/expectations.json').read_text())['cases']}
reviews = json.loads((folder / 'semantic-reviews.json').read_text())
observed = [campaign.inspect_case(root, frozen, row) for row in frozen['cases']]
rows = [campaign_metrics.compare_case(row, expected[row['issue']], review) for row, review in zip(observed, reviews, strict=True)]
reproduced = campaign_metrics.aggregate(rows, frozen['campaign_id'], frozen['configuration_sha256'])
assert reproduced == json.loads((folder / 'comparison.json').read_text())
print('PASS: 168 frozen files, ten isolated packages and exact final comparison; no inference')
PY
```

This verifies saved decisions and reproduces aggregation using the retained semantic assessments; it does not independently repeat qualitative judgement. `python3 -B scripts/check_campaign.py verify --freeze-sha256 0c0ca76cd19e5adca0c5ebfc2be40e531a1ecbda5a4a546ada9f42d125d21a5f` additionally requires the original pinned CLI binary at the recorded host path. Its absence on another machine is an engine-pin portability limit, not permission to weaken the freeze. Do not use `compare` in the original evidence tree: it intentionally creates a new comparison record.

The frozen `scripts/verify_baseline.py` predates G documentation and only allowlists the evaluated file layout. G's audit records its literal full-tree rejection and a separate, explicit projection check excluding only G's new documentation/measurement paths; upstream/source/golden/evidence integrity are also checked against the complete candidate tree. Do not edit the frozen verifier to conceal this packaging limitation. The data-only [development archive](development-evidence.tar.gz) has SHA-256 `33e5bf68145a83871ff94324b25694a780e326e119ad48f979d78e8b75620531`; inspect members as data, never execute historical code. Omitted old Python copies have hashes, which cannot reconstruct them; the final evaluated source is present.

## A future model rerun requires separate authorisation

G grants no new provider requests. Preserve this campaign unchanged. Before a future rerun, Darren must approve a distinct campaign/attempt plan and recorded append-only quota decision; the retained local allowance is exhausted at 51/51. Never reset/refund it or reuse existing run IDs. Register a new configuration/freeze if evaluated bytes change and run a new full ten-case campaign before claiming final accuracy.

An authorised operator would verify the pinned CLI `0.154.0` binary hash from `freeze.json`, compatible host/runtime, existing ChatGPT authentication and reviewed settings, then invoke `python3 -B scripts/clarifier/c_preview.py --case <approved-issue-id>` under a new declared campaign. The helper stages one allowlisted case in a fresh private workspace, loads identical canonical skill bytes through the Codex adapter, admits quota before inference and records the exact no-tool request. Do not give the evaluated session the repository, its history, this guide, expectations, reviews, measurement or later discussion. Preserve failed attempts and verify source/input hashes before and after. Provider same-ID backend changes cannot be pinned or detected from the ID alone; deterministic replay is not model-output reproducibility.

## Operations and accountable review

The authored [triage workflow](../.github/workflows/clarifier-triage.yml) is a GitHub Actions platform equivalent, not gh-aw; a compiled `.lock.yml` is inapplicable. Manual `workflow_dispatch` defaults to preview. The [policy](../scripts/clarifier/controls/policy.py) and [identity checks](../scripts/clarifier/controls/identity.py) bind repository `peckyboi2/eslint`/1435519573, owner/caller/rerun initiator `peckyboi2`/234542779 and `refs/heads/main`. The candidate branch `ai-workflow` is for review; publishing it does not authorise promotion to the trusted ref.

Preview preserves proposals locally with no posting target or public action. `no_action`, `human_review`, invalid output and denied gates stay publicly silent. Posting is disabled: `LIVE_TARGET.issue` and the approved release are unset, engine/login/state are not provisioned, and the last read-only platform checks found Actions disabled and no registered workflows. Publishing evidence is a separate approval from enabling this agent.

Darren Peck owns configuration, model/skill changes, quota changes, release, output review, stop/restart and any eventual submission. Before future posting, he must separately authorise provisioning and the exact target/release after reviewing all golden and attack results, credentials, caller/ref checks and known failures. No independent output approval is claimed here. Do not add generic model tools or personal posting tokens. Existing CODEOWNERS belongs to upstream; it is not a new branch-protection guarantee.

The model has no tools, filesystem API, MCP server or arbitrary network fetch. A trusted gateway fixes the provider destination and rejects tool calls; the Python/Codex host itself is not OS-jailed and host egress/firewall containment is unverified. Job-scoped state/output permissions remain broader than one endpoint, so trusted-code compromise is outside the model capability guarantee. Only deterministic handlers can update the non-forced state ref or post the single allowed comment; no closure/deletion/merge/force-push interface is exposed to the model.

Hosted admission caps are 10/rolling 24h and 20/campaign; failures consume reservations with no refund or automatic delayed retry. One active/one pending triage configuration may supersede older pending dispatches; live queue behaviour remains unverified. Arriving issues alone trigger zero inference, including 300 in a week. Manual dispatches remain quota-gated and excess work stays with humans. Local historical extensions are separately recorded and cannot override hosted caps.

Bounds are 64 KiB input, one provider request, 300-second inference timeout, 16 KiB output, 2 MiB provider response and one comment/report of at most 2,000 characters including trusted attribution. The inference job has a 15-minute timeout; other jobs have their declared smaller bounds. Count/runtime limits do not impose a hard dollar/token cap or guarantee provider-side cancellation. Workflow artifacts declare 30-day retention; actual hosted retention is untested and cancellation may prevent upload. Submission evidence is retained in Git.

The [ledger](../scripts/clarifier/controls/ledger.py), [posting intent](../scripts/clarifier/outputs/posting_intent.py) and [handler](../scripts/clarifier/outputs/posting.py) reserve quota/intent before effects, enforce lifetime duplicate protection, bind trusted target/source hashes, and recheck enabled/release state. An edit or stop can still race between the final check and HTTP POST; accepted/in-flight writes require inspection.

For a lost posting response, keep disabled and preserve the reserved/uncertain intent. Darren must inspect the complete comment list on the exact sandbox issue and match one trusted marker, verified bot identity and comment ID/URL, with reason/time recorded through a trusted state transaction and the reconciliation helper. Missing, multiple, malformed or incomplete evidence stays blocked. Never delete the lifetime intent or automatically repost. See [reconciliation simulation](checks/gate-e-20261028/task47-reconciliation-simulation.json) and its retained typed-denial correction.

From a phone, after separately authorised provisioning: sign in as `peckyboi2`, open the sandbox Actions tab, select **Stop sandbox clarification**, then **Run workflow** on `main`. Inspect the independent [stop workflow](../.github/workflows/clarifier-stop.yml) result: ledger and workflow disabled, active AND pending runs cancelled/force-cancelled, unresolved runs listed. Check marker-bearing comments/in-flight intents; cancellation cannot undo accepted writes. Keep disabled, revoke inference access if necessary and reconcile before restart. The stop job shares no triage lock/dependency; runner scheduling can still delay it. [Task 48](checks/gate-e-20261028/task48-phone-stop-fallback.json) is a simulation, not an observed phone stop; tasks 46 and 48 remain live-blocked.

Before promotion, after model/configuration/tool changes and weekly while enabled, Darren reviews all ten golden decisions and both comments plus all attacks, errors, drift and usage. The [regression checker](../scripts/check_regression.py) fails closed on changed identity, missing evidence or judgement failure; the [drift policy](checks/gate-e-20261028/task49-drift-review-policy.json) and synthetic failure/correction demonstrate detection only. No scheduled inference is installed. #19924 currently blocks promotion; semantic review is not automated approval.

## Earlier evidence and failures

All directories under `runs/`, `platform-tests/` and `checks/` are retained with original bytes; their inventories identify outputs, configuration/source hashes, errors and verification type. They are development/control history, never substitutes for the ten F attempts. Platform-test fixtures and local admissions are not live GitHub actions. No earlier Python snapshot is imported or executed.

| History | Entry point / retained finding |
| --- | --- |
| A/B/R1/R2 and C | [data-only archive](development-evidence.tar.gz), [Gate C](checks/gate-c-20261028/); archived failures and skill/isolation checks, plus blocked platform preview/post/replay fallbacks. |
| D wording failure | [#20606 v3](runs/20261028T050239Z-453163ef/comparison.json): correct decision but omitted build command; [v5 correction](runs/20261028T054714Z-72edea74/comparison.json) belongs to v5. |
| D uncertainty failures | [#19924 v3](runs/20261028T050356Z-3f74565e/comparison.json), [v5](runs/20261028T054822Z-b5ee3ae0/comparison.json), [v6](runs/20261028T060932Z-f77abb9c/comparison.json). Retain failed labels and output-informed [rubric audit](checks/gate-d-rubric-review-20261028/verification.json). |
| E full challenge | [Gate E review/control index](checks/gate-e-20261028/gate-e-review.json), [v6 attack review](checks/gate-e-20261028/task40-model-review.json), [v7](checks/gate-e-20261028/task42-v7-attack-review.json), [v8](checks/gate-e-20261028/task47-v8-attack-review.json). All three attacks passed actual no-tool previews under each configuration; one initial loopback/access failure before provider dispatch is retained. No final-v9 attack inference is claimed. |
| E defects and corrections | [owner-name correction](checks/gate-e-20261028/task42-correction-freeze-v2.json), [malformed reconciliation correction](checks/gate-e-20261028/task47-correction-freeze-v2.json), initial failing test logs and subsequent passing records remain alongside them. |
| E live limits and scenario | [queue fallback](checks/gate-e-20261028/task46-queue-simulation.json), [phone fallback](checks/gate-e-20261028/task48-phone-stop-fallback.json), [drift challenge](checks/gate-e-20261028/task49-review-failure-v1.json), [300-report scenario](checks/gate-e-20261028/task50-scenario.json). Simulations do not complete live tests. |
| F preparation failures | [corrections](checks/gate-f-20261028/pre-freeze-corrections.json) retains initial test/inventory failures; final source identity was frozen before the ten successful executions. |

The G audit and exact local candidate file list are under `checks/gate-g-20261028/`. Publication, remote commit link, deployment and eLearn submission remain subject to Darren's separate review and authorisation.
