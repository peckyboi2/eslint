# Live hosted smoke test, 2026-10-29

The automatic integration passed once at [sandbox issue 1](https://github.com/peckyboi2/eslint/issues/1), [Actions run 40816597353](https://github.com/peckyboi2/eslint/actions/runs/40816597353), using commit `f2a56cbe6aedc1960f62035a9cad26fa77251b60` and the original `hosted-preview-v11` configuration. Artifact completeness failed because one hidden instruction file was omitted. This synthetic integration case does not score semantic accuracy or replace the ten historical cases.

Read these files in order:

1. [Acceptance criteria](metadata/smoke-acceptance.json): recorded before inspecting the model response; one request, successful jobs and no public agent actions.
2. [Assessment](assessment.json): integration result, separate artifact failure, model, usage, instruction checks and remaining gaps.
3. [Run](metadata/run-final.json) and [jobs](metadata/jobs-final.json): real issue event, attempt 1, exact code commit and successful gate, admission and inference jobs.
4. [Preview record](artifacts/preview-40816597353/preview/record.json), [request](artifacts/preview-40816597353/preview/request.json) and [validation](artifacts/preview-40816597353/preview/validation.json): one actual `gpt-6.1-sol` request, 2,567 tokens, no tools or public actions, observed `human_review` result. Cost is unknown.
5. [Loader](artifacts/preview-40816597353/preview/loader.json) and [native probe](artifacts/preview-40816597353/preview/native-load-probe.json): canonical skill matched after native outer-whitespace trimming; host context and native tools were excluded from the provider request.
6. [State receipt](metadata/state-final.json), [comments receipt](metadata/comments-final.json), [workflow states](metadata/workflows-final.json) and [action policy](metadata/allowed-actions-final.json): one admission, posting disabled, zero issue comments, inherited workflows disabled and three permitted action pins. These are observations at capture time, not a live status query.

## Original artifact failure and separate recovery

All 32 downloaded artifact files and 19 selected metadata files were copied byte for byte. The preview's original [artifact manifest](artifacts/preview-40816597353/preview/artifact-hashes.json) contains 26 entries: 25 present files match, and `configuration/.claude/skills/eslint-clarification/SKILL.md` is missing. GitHub's upload action excluded the hidden `.claude` directory. The downloaded artifact remains unchanged and incomplete.

The missing canonical skill was recovered locally from the exact run commit into [recovery/configuration/.claude/skills/eslint-clarification/SKILL.md](recovery/configuration/.claude/skills/eslint-clarification/SKILL.md). [Recovery provenance](recovery/provenance.json) records its matching SHA-256. This separate copy supports inspection; it does not turn the failed upload into a complete original artifact. All 60 recorded configuration and source hashes were checked against that exact commit, and the recorded configuration aggregate was recomputed successfully.

## Integrity and limits

[Original-copy hashes](original-copy-sha256.json) identify the untouched copies. [Package hashes](SHA256-MANIFEST.json) cover this evidence directory except the manifest itself. [Credential scan](credential-scan.json) records a local pattern scan with no findings; the actual API key was never available locally, and a pattern scan cannot prove absence of every possible credential.

This run tests the original v11 integration only. Historical accuracy, adversarial decisions, public posting, live cancellation and phone stopping remain separate checks. Any later artifact-export fix needs its own configuration identity and validation. Packaging and recovery made no network or model calls.
