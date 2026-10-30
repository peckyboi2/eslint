# Evaluation inputs, results and evidence

The current GitHub-hosted workflow completed its [historical and adversarial evaluation](hosted-v11-20261029/README.md): **9/10 historical decisions matched**, **3/3 adversarial cases matched**, both expected clarification proposals passed assistant wording review, and no model tools/public actions occurred. **#19924 remains a recorded failure** (`human_review` expected, `no_action` returned). All 13 attempts used the same recorded code and settings on GitHub and original labels; no case was retried or replaced. Reviews are assistant assessments, not independent human approval.

The owner-approved evaluator temporarily used a 60-second window, then [restored it to 24 hours and disabled the manual replay workflow](../hosted-v11/campaign-20261029/restoration.json). The automatic issue route retained its 24-hour window throughout. All 15 hosted reservations remain; five runs remained under the total budget at completion. Current results, original artifacts, comparisons, usage, test logs and offline reproduction instructions are in the linked bundle. The two retained automatic opening tests are integration evidence, separate from these ten-case results.

Use `python3 -B scripts/verify_submission.py` for current source/evidence and separately labelled replay of the earlier local evaluation, `python3 -B -m unittest discover -s scripts/automatic_tests -v` for current evidence tests, and `python3 -B scripts/verify_automatic.py --tests` for current safety tests. These checks are offline. `--safety-tests` on the submission verifier runs tests for the earlier local implementation. The sections below retain **earlier local operations and status only**; current hosted operation is described in the campaign guide.

## Earlier local evaluation and operations

This is the current entry point. The [original evaluation README](README.md) records the pre-inference state of 27 October 2026; its wording and all original bytes remain frozen. The additive [earlier local evaluation results](final-results-v9/README.md) contain actual outputs, transcripts, run records, comparisons and test logs from the completed evaluation. It is evaluator-only and is not part of the original input set.

## Inputs, results and failures

| Material | Location |
| --- | --- |
| Ten historical inputs and provenance | [Prepared inputs](prepared-inputs/), [package manifest](prepared-inputs/manifest.json), per-case `snapshot.json` and [original input and expectation hashes](FREEZE.json). Supporting text for #19847 and #19118 is included. Do not execute report code. |
| Expectations recorded before inference | [Labels](expectations.json), [accepted reasons](expected-decision-review.md), [comment criteria](comment-quality.md). Labels remain 2 clarify / 7 no_action / 1 human_review. The original research plan is retained in Git history. |
| Ten final actual attempts | [Versioned bundle and case table](final-results-v9/README.md), including outputs, transcripts, validated routes, records and per-case comparisons. Each row also links its full original run. |
| Final comparison and test log | [Comparison export](final-results-v9/checks/comparison.json), [semantic reviews](final-results-v9/checks/semantic-reviews.json), [172-test log](final-results-v9/checks/pre-freeze-tests-v3.txt), [original local evaluation review](../checks/gate-f-20261028/gate-f-review.json). |
| Adversarial evidence | [Three local adversarial tests and their review](adversarial-v9-20261029/README.md): fabricated approval, poisoned support and simulated tool instructions, **3/3 passed**. This separately authorised 29 October supplement preserves the original historical campaign. [Earlier control-test records](final-results-v9/README.md#adversarial-evidence) and all defects remain available through [earlier evidence](../README.md#earlier-evidence-and-failures). |
| Earlier failures and original evidence | [Failure/history index](../README.md#earlier-evidence-and-failures), [retained runs](../runs/), [checks](../checks/), [data-only archive](../development-evidence.tar.gz). Repeated successful development runs and synthetic platform-test records remain in Git history. Do not execute archived content. |
| Final freeze and audit | [168-file local evaluation snapshot](../checks/gate-f-20261028/freeze.json), [2,710 earlier evidence hashes](../checks/gate-g-20261028/preserved-evidence-sha256.json), [submission packaging review](../checks/gate-g-20261028/review.md). These historical status records are not rewritten by this packaging correction. |
| Need measurement and operations | [September cohort](../measurement/README.md), [operating guide and limits](../README.md), [design](../../DESIGN.md). |

The earlier local evaluation used `gpt-6.1-sol` with `xhigh` reasoning and Codex CLI 0.154.0; its technical configuration names remain in the saved records. Ten single predeclared attempts completed with **9/10 decision matches**, 2/2 comment-quality passes and zero public writes.
#19924 remains expected `human_review`, actual `no_action`, a failed match.
#19847 remains `no_action`. Assistant semantic reviews are saved assessments, not independent/blinded human approval. The separate September 0/10 is an observation of maintainer clarification requests, not evaluation accuracy.

## Offline reproduction for the complete submission

From the repository root, with Git, retained Git history and Python 3.11+:

```sh
python3 -B scripts/verify_submission.py
python3 -B -m unittest discover -s scripts/submission_tests -v
python3 -B scripts/verify_submission.py --safety-tests
git diff --check
```

The current [verifier](../../scripts/verify_submission.py) checks the actual complete tree, original input inventory and combined hash, all 168 final frozen files, all 2,710 earlier evidence hashes, original run inventories/configurations, data-only archive, export provenance and byte equality, required files, DESIGN line limit and current local links. It stages all ten exact allowlisted packages in disposable directories, then reconstructs every per-case comparison and the aggregate from saved decisions and saved semantic assessments. It requires the faithfully reproduced 9/10 result, including #19924's failure; it does not require 10/10. No engine binary is needed.

The safety-suite command runs the unchanged 172 historical tests in a disposable local copy because some tests create synthetic platform records. It leaves this checkout intact. The verifier tests also use a disposable local clone/copy and alter inputs, expectations, results, manifests, source, packaging and navigation to check that corruption is rejected. [Saved packaging check records](../submission-checks-v1/) contain the current verification and test results.

These checks invoke no model, network, GitHub or submitted reproduction code. They replay saved evidence and do not independently repeat qualitative judgement or establish hosted enforcement. They also verify the [additional local adversarial tests](adversarial-v9-20261029/README.md), including their predeclared plan, three exact requests, results and separate reservation receipts. A fresh model rerun needs separate authorisation, new campaign identifiers and quota; follow the [future-rerun instructions](../README.md#a-future-model-rerun-requires-separate-authorisation). The original local ledger remains exhausted at 51/51; the separately authorised supplement is exhausted at 3/3.

## Packaging and historical commands

The [export manifest](final-results-v9/exports.json) binds each copied file to its original path, SHA-256 and original local candidate commit. Only selected results and logs are copied (about 348 kB); inputs, settings, requests, skill-load probes, supporting files and full record inventories stay in their original locations. The bundle's nested attributes preserve exported bytes across Git checkouts. Original freezes are unchanged; this bundle has its own version and manifest.

`python3 -B scripts/verify_baseline.py` remains the historical evaluated-layout check advertised by the frozen instructions. It rejects final documentation, measurement and now additive golden packaging; its original [literal failure](../checks/gate-g-20261028/full-tree-baseline.txt) and [projection record](../checks/gate-g-20261028/baseline-projection.json) remain evidence. A projection pass is not a complete-tree pass. Use the current command above; no historical check is edited, hidden or represented as passing this tree.

The frozen [package selector](../../scripts/clarifier/inference/packages.py) and [staging helper](../../scripts/clarifier/inference/staging.py) still export only one approved input package. This index, final results, expectations, reviews, measurement, later discussion, parent checkout and Git history must never enter an evaluated session. The new verifier stages every case and checks those exact inventories. Hosted posting/identity, queue and phone cancellation and other live gaps remain as documented in DESIGN and the operating guide; this fix makes no new live claim.
