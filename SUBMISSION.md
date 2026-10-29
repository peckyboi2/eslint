# Current CS467 submission entry point

Current runtime is **hosted-preview-v11-artifacts-v2**: [hosted evidence and operations](evals/hosted-v11/README.md). Its [automatic GitHub smoke run](evals/hosted-v11/live-smoke-artifacts-v2-20261029/README.md) passed: one OpenAI request, `human_review`, 2,910 tokens, all 26 artifact entries verified and zero public comments. The [preceding v11 run](evals/hosted-v11/live-smoke-20261029/README.md) retains its missing-hidden-file failure and separate recovery. Earlier ten-case v9 results remain historical, not current accuracy.

The [v10 automatic candidate](evals/automatic-v10/README.md) and its 212 tests are preserved history. Use `python3 -B scripts/verify_submission.py` for current bytes plus exact retained v9 verification, `python3 -B scripts/verify_automatic.py --tests` for current infrastructure tests, and `python3 -B scripts/verify_submission.py --safety-tests` for frozen v9 tests. The remaining sections retain v9 operations and status; current hosted operations are in the linked guide.

## Retained v9 evidence and operations

Start at [the golden submission index](evals/golden/INDEX.md) for historical inputs, pre-recorded expectations, all ten final attempts, actual outputs, transcripts, comparisons, adversarial evidence, retained failures and reproduction instructions.

[DESIGN.md](DESIGN.md) gives the justification; [operations](evals/README.md) gives the control limits and future operator instructions.

The [29 October v9 attack supplement](evals/golden/adversarial-v9-20261029/README.md) now records three additional authorised actual previews on the unchanged frozen inference configuration: **3/3 passed**, zero tool calls/public writes. A separate three-slot reservation envelope preserves the original exhausted 51-run ledger. Historical results remain **9/10**. The current offline verifier also checks the supplement's pinned evidence.

Run from this repository root with Git and Python 3.11+ (standard library only):

```sh
python3 -B scripts/verify_submission.py
python3 -B -m unittest discover -s scripts/submission_tests -v
python3 -B scripts/verify_submission.py --safety-tests
git diff --check
```

The current verifier checks the complete tree against local candidate `884acc7031a761eb45e5fe7ac186d43d5bed5901`, both original freezes, all 2,710 earlier evidence hashes, exported bytes, isolation, navigation and exact saved comparison. It permits the two current-document edits and the named additive packaging files; it removes no files. Keep the repository's Git history when cloning for verification. No pinned CLI binary, authentication, Node installation, inference or network is needed.

Final decision matches remain **9/10**. #19924 is expected `human_review`, actual `no_action`; this structural verification must pass while preserving that failure. The separate September cohort remains 0/10 observed maintainer clarification requests.

The root README, AGENTS.md, golden-v1 README and `scripts/verify_baseline.py` are frozen historical files. Their baseline command predates final additions and is **not the current complete-tree command**. Its [recorded failure](evals/checks/gate-g-20261028/full-tree-baseline.txt) and [explicit historical projection](evals/checks/gate-g-20261028/baseline-projection.json) are preserved. See [the packaging note](evals/golden/INDEX.md#packaging-and-historical-commands).

This is the permitted coding-assistant dry-run submission, with actual local inference and labelled platform simulations. Hosted bot identity/posting, queue and phone cancellation remain unverified. Posting stays disabled. This packaging task made no model/provider call, quota change, public write, deployment or submission.
