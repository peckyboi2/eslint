# Live artifact-retention smoke test, 2026-10-29

The automatic integration and original artifact completeness passed at [sandbox issue 2](https://github.com/peckyboi2/eslint/issues/2), [Actions run 40818202827](https://github.com/peckyboi2/eslint/actions/runs/40818202827), using commit `0db9c40737e7fca31d79d476bc36ff30b714c133` and `hosted-preview-v11-artifacts-v2`. This additional run was authorized to test the hidden-file upload fix. It was not a semantic retry or a historical accuracy evaluation.

Read these files in order:

1. [Acceptance criteria](metadata/smoke-acceptance.json): recorded before issue creation and inference; expected complete original artifacts, native skill loading, one provider request and no public agent actions.
2. [Assessment](assessment.json): integration and artifact results, usage, configuration checks and remaining gaps.
3. [Run](metadata/run-final.json), [jobs](metadata/jobs-final.json) and [original workflow log](metadata/workflow-log.txt): real issue-opening event, attempt 1, exact code commit and successful gate, admission and inference jobs.
4. [Preview record](artifacts/preview-40818202827/preview/record.json), [request](artifacts/preview-40818202827/preview/request.json) and [validation](artifacts/preview-40818202827/preview/validation.json): one actual `gpt-6.1-sol` request; 2,227 input tokens, 683 output tokens and 2,910 total tokens; no tools, errors or public actions. Cost is unknown. The observed decision was `human_review`; correctness was not scored.
5. [Original retained skill](artifacts/preview-40818202827/preview/configuration/.claude/skills/eslint-clarification/SKILL.md), [loader](artifacts/preview-40818202827/preview/loader.json) and [native probe](artifacts/preview-40818202827/preview/native-load-probe.json): canonical skill present in the downloaded artifact and matched after native outer-whitespace trimming; host context and native tools were excluded from the provider request.
6. [State before](metadata/state-before.json), [state after](metadata/state-final.json), [comments](metadata/comments-final.json) and [workflow states](metadata/workflows-final.json): admissions increased from one to two, posting stayed disabled, no posts or issue comments appeared, and inherited workflows stayed disabled. These receipts describe capture time, not a live status query.

## Integrity and the earlier failure

All 33 downloaded artifact files and 15 metadata files, including the actual workflow log, were copied byte for byte. All 26 entries in the original [artifact manifest](artifacts/preview-40818202827/preview/artifact-hashes.json) are present and match, including `configuration/.claude/skills/eslint-clarification/SKILL.md`. No recovery or insertion into the original artifact was needed. All 60 recorded configuration and source hashes match the exact run commit, and the configuration aggregate was recomputed successfully.

The [first run](../live-smoke-20261029/README.md) retains its original missing-file failure and separate recovery. This run validates the later upload fix under its own configuration identity; it does not rewrite that earlier evidence.

[Original-copy hashes](original-copy-sha256.json) identify untouched copies. [Package hashes](SHA256-MANIFEST.json) cover this evidence directory except the manifest itself. [Credential scan](credential-scan.json) records a local byte-pattern scan; the actual API key was never available locally and matched values are never printed. Pattern matching cannot prove absence of every possible credential.

## Platform warning and limits

The workflow log reports that the pinned actions targeting Node.js 20 were forced to execute on Node.js 24. All jobs succeeded. This warning demonstrates that pinned action source does not pin GitHub's runner or action runtime; it is recorded as a platform limitation, not an execution failure.

This run does not establish historical accuracy, adversarial correctness, public posting, live quota exhaustion, concurrent execution or phone stopping. Those require separate evidence. Packaging, integrity checks and this assessment made no network or model calls.
