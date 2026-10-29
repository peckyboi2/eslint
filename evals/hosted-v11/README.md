# Hosted preview: preparation, activation and artifact correction

Current runtime is `hosted-preview-v11-artifacts-v2`. The preceding `hosted-preview-v11` completed one real automatic integration test on 29 October 2026. The current variant changes artifact retention and its version identity; it has no additional provider call or new ten-case evaluation.

## Observed live test

Open the [smoke evidence guide](live-smoke-20261029/README.md), [GitHub run](https://github.com/peckyboi2/eslint/actions/runs/40816597353) and [synthetic issue](https://github.com/peckyboi2/eslint/issues/1). The run used immutable source commit `f2a56cbe6aedc1960f62035a9cad26fa77251b60`: gate, admission and inference succeeded. Codex CLI 0.154.0 loaded the canonical skill; one request to `gpt-6.1-sol` returned `human_review`, with 2,216 input and 351 output tokens. Cost was unavailable. Tools and public actions were empty; the issue had zero comments.

The smoke is integration evidence, with no pre-guaranteed semantic answer. It is not another historical accuracy case. The downloaded preview artifact omitted `configuration/.claude/skills/eslint-clarification/SKILL.md` because upload excluded hidden paths. Original downloads remain unchanged. The evidence guide identifies a separate recovery from the exact Git source and its matching hash. The live run therefore passed integration but failed artifact completeness.

## Current correction and checks

The [workflow](../../.github/workflows/clarifier-triage.yml) now sets `include-hidden-files: true` only for `evals/automatic-workflow`. Private engine directories and credentials are outside that output directory. [Static audit](../../scripts/clarifier/github/workflow_audit.py) and mutation tests require the exact path and hidden-file setting; broad repository upload is rejected. The [236-test log](safety-tests-artifacts-v2.txt) covers synthetic controls, not hosted upload of the corrected variant. No second smoke request was made.

The [current manifest](candidate.json) identifies this variant separately. Its zero-call/unverified flags refer only to the new variant. The unchanged [pre-activation manifest](pre-activation-candidate.json) identifies the configuration used by the real smoke; it is historical preparation metadata, not a claim that no later activation occurred. The [first review](preparation-review-v1.json), [failed initial manifest](failed-preparation-v1.json), original tests and [revision-2 tests](safety-tests-revision2.txt) remain unchanged. The first review caught a credential-environment inheritance gap before live execution; revision 2 sanitized the separate CLI version probe.

## Runtime and permissions

The [hosted profile](../../scripts/clarifier/config/hosted.json) and [release evidence](runtime-release.json) pin the official Linux archive and actual x86_64 ELF executable. The [installer](../../scripts/clarifier/inference/hosted_install.py) bounds time, size and redirects, rejects unsafe archive entries, verifies both hashes and architecture, installs privately under `RUNNER_TEMP`, and exports that directory through `GITHUB_PATH`.

Only the trusted inference command receives `CLARIFIER_PROVIDER_KEY`. The native model process and separate version probe receive neither that key nor the GitHub token. Gate and inference have read permissions; only admission can append state. No issue-write/comment job exists in automatic intake. The approval workflow remains disabled and release-blocked. No OS jail or host firewall is claimed; model/provider backend revision and runner image remain mutable.

## Enabled sandbox and operator steps

Only **Sandbox clarification preview** and **Stop sandbox clarification** are enabled in `peckyboi2/eslint`. Inherited workflow files are preserved but their remote execution is disabled. Actions permits only the three exact reviewed checkout/upload/download action commits. Issues is enabled. `triage-state` was initialized separately from historical local reservations, then an owner-attributed decision enabled previews with posting false.

A new eligible ordinary User-authored issue titled exactly with `Bug:` runs automatically. Event/API identity and unchanged input are checked before inference; unsupported inputs are denied. Limits are 10 admissions per rolling 24 hours and 20 per campaign; failed admitted runs consume their slot, with no automatic retry or refund. One slot was consumed by the smoke. Darren subsequently authorized one additional genuine issue-opening smoke after this fix is published, solely to verify complete artifact upload. That second request is pending at this preparation freeze; no semantic retry or public comment is authorized.

To inspect future runs: **Actions → Sandbox clarification preview → run → Artifacts → preview-<run ID>**. Read `preview/record.json`, raw/validated output, loader and request evidence. `no_action` and `human_review` remain silent; even `clarify` is only a saved proposal. Opening an issue does not enable posting.

To stop from a phone: sign in as owner, open **Actions → Stop sandbox clarification → Run workflow**, select `main`, then inspect disabled ledger flags, preview/approval disablement, cancellation results and unresolved running work. Disabling alone does not cancel active runs. Provider work can outlive cancellation. Keep disabled until owner review; never reset/refund state. Phone use, live stop/cancellation and queue overflow remain untested.

## Evaluation boundaries and reproduction

Run `python3 -B scripts/verify_submission.py` for current-tree and historical evidence checks, `python3 -B scripts/verify_automatic.py --tests` for current safety tests, and `python3 -B -m unittest discover -s scripts/automatic_tests -v` for verifier/allowance tests. These commands are offline and invoke no model. The corrected artifact setting requires a later separately authorized hosted execution to observe its actual upload.

[Preservation](preservation.json) retains all 33 original v10 records and 54 prior local reservations. V9's actual ten cases still score 9/10, with #19924's failure retained, and its three-attack supplement scores 3/3. Those results do not evaluate current hosted bytes. The v10 unexecuted 13-call proposal cannot authorize a current run. Freeze and obtain authorization for a new complete evaluation before claiming current accuracy. Darren owns configuration, budgets, enablement and final review. New implementation/evidence documentation is AI-assisted and requires his verification.
