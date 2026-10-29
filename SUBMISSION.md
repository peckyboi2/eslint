# Current CS467 submission entry point

Current runtime **hosted-preview-v11-artifacts-v2** completed its [hosted golden campaign](evals/golden/hosted-v11-20261029/README.md): **9/10 historical decisions matched**, **3/3 adversarial cases matched**, both expected clarification proposals passed assistant wording review, and no model tools/public actions occurred. **#19924 remains a recorded failure** (`human_review` expected, `no_action` returned). All 13 attempts used the same frozen hosted runtime and original labels; no case was retried or replaced. Reviews are assistant assessments, not independent human approval.

The owner-approved evaluator temporarily used a 60-second window, then [restored it to 24 hours and disabled the manual replay workflow](evals/hosted-v11/campaign-20261029/restoration.json). The automatic issue route retained its 24-hour window throughout. All 15 hosted reservations remain; five campaign slots are left. Current results, original artifacts, comparisons, usage, test logs and offline reproduction instructions are in the linked bundle. The two retained automatic opening tests are integration evidence, separate from these ten-case results.

Use `python3 -B scripts/verify_submission.py` for current source/evidence and separately labelled v9 replay, `python3 -B -m unittest discover -s scripts/automatic_tests -v` for current evidence tests, and `python3 -B scripts/verify_automatic.py --tests` for current safety tests. These checks are offline. `--safety-tests` on the submission verifier runs historical v9 tests. The sections below retain **historical v9 operations/status only**; current hosted operation is described in the campaign guide.

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

The root README, golden-v1 README and `scripts/verify_baseline.py` retain historical wording. Current AGENTS.md and CONTRIBUTING.md describe the automatic preview route; their evaluated v9 versions remain preserved in Git. The old baseline command predates final additions and is **not the current complete-tree command**. Its [recorded failure](evals/checks/gate-g-20261028/full-tree-baseline.txt) and [explicit historical projection](evals/checks/gate-g-20261028/baseline-projection.json) are preserved. See [the packaging note](evals/golden/INDEX.md#packaging-and-historical-commands).

This is the permitted coding-assistant dry-run submission, with actual local inference and labelled platform simulations. Hosted bot identity/posting, queue and phone cancellation remain unverified. Posting stays disabled. This packaging task made no model/provider call, quota change, public write, deployment or submission.
