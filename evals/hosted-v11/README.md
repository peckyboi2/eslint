# Hosted preview preparation v11

This candidate prepares API-key inference for real sandbox issue events. The secret name `CLARIFIER_PROVIDER_KEY` was confirmed through GitHub metadata; its value was never read. No model request, remote configuration change, issue/comment, commit or push occurred during preparation.

## What changed

- [Hosted profile](../../scripts/clarifier/config/hosted.json) pins Codex CLI 0.154.0, its official Linux archive and the actual x86_64 ELF executable. [Release evidence](runtime-release.json) records independent archive/payload hashes without executing the Linux file on macOS.
- [Installer](../../scripts/clarifier/inference/hosted_install.py) accepts only the fixed official release, bounds download size/time/redirects, rejects unsafe archive members, and verifies payload SHA-256 and ELF architecture before `--version`. It installs in a fresh private directory under `RUNNER_TEMP` and explicitly exports that directory through `GITHUB_PATH`.
- [Workflow](../../.github/workflows/clarifier-triage.yml) installs before inference and supplies the provider secret only to that one trusted gateway command. The native model process and the separate CLI version probe receive neither the API key nor GitHub token. Only admission has contents-write; preview has no issue-write/comment job. Gate/admission/inference have explicit read permissions for repository contents, issue snapshots and Actions run verification.
- Temporary staging and active safety-test fixtures use a resolved host temporary directory on macOS/Linux instead of a hardcoded Mac path. The canonical skill, model ID/effort, historical inputs, accepted outcomes, hosted quotas and posting block are unchanged.

## Verification and preserved history

The [235-test safety suite](safety-tests-revision2.txt) passed in a disposable checkout with synthetic GitHub/provider exchanges. These checks do not establish model accuracy, real API access or hosted token enforcement. The [24 verifier/allowance corruption tests](verifier-tests-v2.txt) also passed in a disposable candidate. The installer inspected the actual downloaded archive and payload without executing them. Its live download, Linux CLI startup, native skill loading and provider response still need a hosted test.

[Preservation](preservation.json) pins all original v10 preparation records and 54 prior reservations unchanged. The new [candidate manifest](candidate.json) identifies current v11 bytes separately. The v10 proposal and unexecuted evaluation freeze remain historical, not evidence that v11 was evaluated. Older runtime hashes identify old bytes; they do not reconstruct omitted working-tree source. Exact v9 Git/overlay verification still reproduces 9/10 and its three-attack supplement, including the retained #19924 failure. [Frozen v9 tests](frozen-v9-tests.txt) remain separate.

Run `python3 -B scripts/verify_submission.py` for current-tree/historical evidence verification, `python3 -B scripts/verify_automatic.py --tests` for the current safety suite, and `python3 -B -m unittest discover -s scripts/automatic_tests -v` for corruption/allowance tests. All are offline; none invokes the provider. The v10 13-slot local evaluation proposal is superseded for current v11 and cannot authorise a v11 run. Freeze and approve a new final hosted evaluation before claiming new accuracy.

The [first preparation review](preparation-review-v1.json) records a credential-environment inheritance gap caught before any hosted execution or provider call. Its [original manifest](failed-preparation-v1.json) and initial passing tests remain preserved. Preparation revision 2 sanitizes the separate CLI version probe and tests that exact environment boundary.

## Proposed activation payload for owner review

1. Review and commit the exact current candidate, then publish it to the existing sandbox's trusted `main` without rewriting history. Preserve the full ESLint fork and inherited workflow files. Publishing or enabling anything is outside this local preparation.
2. Before enabling Actions, inspect inherited workflows and prepare selective disablement so only the intended preview and emergency stop can run. The approval workflow remains disabled. Enable the repository Issues feature.
3. Create `triage-state` with canonical `ledger.initial(at, reason)`, disabled flags and an owner-attributed bootstrap. Append one accountable `enable-preview` decision with posting false; do not copy/reset the exhausted local ledger. Limits stay ten admissions/rolling 24 hours and twenty/campaign.
4. Enable preview and stop, then create one owner-approved synthetic issue titled `Bug: automatic preview smoke test`. Its first genuine opening should drive gate, admission and inference automatically. Do not edit it during processing or manually rerun it; failed admitted work still consumes its reservation. The smoke test is at most one actual provider request, without semantic retries or any public comment.
5. Retain issue/run/commit URLs, admission and preview artifacts, actual model/usage or error, request and native skill-load evidence. A valid outcome has one matching issue ID/source snapshot and empty tool/public-action lists. No particular semantic decision is pre-guaranteed by the smoke text.
6. Exercise the independent owner-only stop, including active/pending cancellation where possible, and retain actual receipts. Disabling a workflow alone does not cancel its current run; provider work and accepted writes can outlive cancellation. Keep posting disabled. Recovery requires owner review; never reset/refund the ledger or automatically repost.

Until these steps are approved and performed, Actions/state/issue settings and hosted inference remain unverified. A successful smoke run is integration evidence, not the required ten-case correctness evaluation or production promotion. This AI-assisted preparation is subject to Darren's review and accountability.
