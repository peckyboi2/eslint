# Current golden submission index

Current runtime is **hosted-preview-v11-artifacts-v2**: [hosted evidence and operations](../hosted-v11/README.md). Its [automatic GitHub smoke run](../hosted-v11/live-smoke-artifacts-v2-20261029/README.md) passed: one OpenAI request, `human_review`, 2,910 tokens, all 26 artifact entries verified and zero public comments. The [preceding v11 run](../hosted-v11/live-smoke-20261029/README.md) retains its missing-hidden-file failure and separate recovery. Earlier ten-case v9 results remain historical, not current accuracy.

The [v10 automatic candidate](../automatic-v10/README.md) and its 212 tests are preserved history. Use `python3 -B scripts/verify_submission.py` for current bytes plus exact retained v9 verification, `python3 -B scripts/verify_automatic.py --tests` for current infrastructure tests, and `python3 -B scripts/verify_submission.py --safety-tests` for frozen v9 tests. The remaining sections retain v9 operations and status; current hosted operations are in the linked guide.

## Retained v9 evidence and operations

This is the current entry point. The [golden-v1 README](README.md) records the pre-inference state of 27 October 2026; its wording and all original bytes remain frozen. The additive [final-results-v9 bundle](final-results-v9/README.md) contains actual outputs, transcripts, run records, comparisons and test logs from the completed evaluation. It is evaluator-only and is not part of the original input set.

## Inputs, results and failures

| Material | Location |
| --- | --- |
| Ten historical inputs and provenance | [Prepared inputs](prepared-inputs/), [package manifest](prepared-inputs/manifest.json), per-case `snapshot.json` and [golden-v1 freeze](FREEZE.json). Supporting text for #19847 and #19118 is included. Do not execute report code. |
| Expectations recorded before inference | [Labels](expectations.json), [accepted reasons](expected-decision-review.md), [comment criteria](comment-quality.md), [original plan](evaluation-plan.md). Labels remain 2 clarify / 7 no_action / 1 human_review. |
| Ten final actual attempts | [Versioned bundle and case table](final-results-v9/README.md), including outputs, transcripts, validated routes, records and per-case comparisons. Each row also links its full original run. |
| Final comparison and test log | [Comparison export](final-results-v9/checks/comparison.json), [semantic reviews](final-results-v9/checks/semantic-reviews.json), [172-test log](final-results-v9/checks/pre-freeze-tests-v3.txt), [original F review](../checks/gate-f-20261028/gate-f-review.json). |
| Adversarial evidence | [Three actual final-v9 attack attempts and review](adversarial-v9-20261029/README.md): fabricated approval, poisoned support and simulated tool instructions, **3/3 passed**. This separately authorised 29 October supplement preserves the original historical campaign. [Earlier E-v8 exports](final-results-v9/README.md#adversarial-evidence), E-v6/v7 and all defects remain available through [earlier evidence](../README.md#earlier-evidence-and-failures). |
| Earlier failures and original evidence | [Failure/history index](../README.md#earlier-evidence-and-failures), [all original runs](../runs/), [platform simulations](../platform-tests/), [checks](../checks/), [data-only archive](../development-evidence.tar.gz). Do not execute archived content. |
| Final freeze and audit | [168-file F freeze](../checks/gate-f-20261028/freeze.json), [2,710 earlier evidence hashes](../checks/gate-g-20261028/preserved-evidence-sha256.json), [G review](../checks/gate-g-20261028/review.md). These historical status records are not rewritten by this packaging correction. |
| Need measurement and operations | [September cohort](../measurement/README.md), [operating guide and limits](../README.md), [design](../../DESIGN.md). |

Final campaign `final-f-20261028-v9` uses `milestone-f-final-v9`, selected `gpt-6.1-sol` / `xhigh`, Codex CLI 0.154.0. Ten single predeclared attempts completed with **9/10 decision matches**, 2/2 comment-quality passes and zero public writes.
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

The current [verifier](../../scripts/verify_submission.py) checks the actual complete tree, original golden-v1 inventory/aggregate, all 168 final frozen files, all 2,710 earlier evidence hashes, original run inventories/configurations, data-only archive, export provenance and byte equality, required files, DESIGN line limit and current local links. It stages all ten exact allowlisted packages in disposable directories, then reconstructs every per-case comparison and the aggregate from saved decisions and saved semantic assessments. It requires the faithfully reproduced 9/10 result, including #19924's failure; it does not require 10/10. No engine binary is needed.

The safety-suite command runs the unchanged 172 historical tests in a disposable local copy because some tests create synthetic platform records. It leaves this checkout intact. The verifier tests also use a disposable local clone/copy and alter inputs, expectations, results, manifests, source, packaging and navigation to check that corruption is rejected. [Saved packaging check records](../submission-checks-v1/) contain the current verification and test results.

These checks invoke no model, network, GitHub or submitted reproduction code. They replay saved evidence and do not independently repeat qualitative judgement or establish hosted enforcement. They also verify the [v9 supplement](adversarial-v9-20261029/README.md), including its predeclared plan, three exact requests, results and separate reservation receipts. A fresh model rerun needs separate authorisation, new campaign identifiers and quota; follow the [future-rerun instructions](../README.md#a-future-model-rerun-requires-separate-authorisation). The original local ledger remains exhausted at 51/51; the separately authorised supplement is exhausted at 3/3.

## Packaging and historical commands

The [export manifest](final-results-v9/exports.json) binds each copied file to its original path, SHA-256 and original local candidate commit. Only selected results and logs are copied (about 348 kB); inputs, settings, requests, skill-load probes, supporting files and full record inventories stay in their original locations. The bundle's nested attributes preserve exported bytes across Git checkouts. Original freezes are unchanged; this bundle has its own version and manifest.

`python3 -B scripts/verify_baseline.py` remains the historical evaluated-layout check advertised by the frozen instructions. It rejects final documentation, measurement and now additive golden packaging; its original [literal failure](../checks/gate-g-20261028/full-tree-baseline.txt) and [projection record](../checks/gate-g-20261028/baseline-projection.json) remain evidence. A projection pass is not a complete-tree pass. Use the current command above; no historical check is edited, hidden or represented as passing this tree.

The frozen [package selector](../../scripts/clarifier/inference/packages.py) and [staging helper](../../scripts/clarifier/inference/staging.py) still export only one approved input package. This index, final results, expectations, reviews, measurement, later discussion, parent checkout and Git history must never enter an evaluated session. The new verifier stages every case and checks those exact inventories. Hosted posting/identity, queue and phone cancellation and other live gaps remain as documented in DESIGN and the operating guide; this fix makes no new live claim.
