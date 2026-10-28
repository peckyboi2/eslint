# ESLint expected-decision review

Collaborative review of the preserved historical inputs. All ten expected decisions have now been reviewed and accepted before implementation or agent evaluation. These are development and regression expectations. The original research bundle retains its earlier provisional metadata as a record of that research stage; this review records the subsequent decisions.

## Issue #19924 — agreed

- Decision: `human_review`.
- Public output: no comment.
- Evidence: the historical report supplies versions, a command, workload size and a specific error trace. It does not supply a reproduction project or configuration.
- Rationale: the available evidence does not establish that either missing item is necessary for the next triage step. The agent cannot identify a clearly necessary, targeted clarification with sufficient confidence.
- Boundary: `no_action` means the report is judged sufficiently complete for this workflow; `human_review` means uncertainty about whether clarification is needed. Both produce no public comment.
- Agreement: the user accepted this decision and distinction in the review conversation.

## Issue #20373 — agreed

- Decision: `clarify`.
- Public output: at most one targeted clarification comment.
- Evidence: the supplied configuration imports `feEslint` from `@fe/eslint-config` and extends its returned configuration. That shared configuration and a reproduction project are absent.
- Rationale: the visible configuration does not establish the complete plugin setup that produces the two reported errors. Request the missing shared configuration and dependency setup without diagnosing their cause.
- Illustrative comment: “Could you share a minimal reproduction that includes the configuration returned by `@fe/eslint-config`, plus its `package.json` and lockfile? The supplied configuration depends on that shared configuration, so we cannot reconstruct the setup from the snippet alone.”
- Agreement: the user accepted `clarify` after reviewing the evidence and proposed request. Wording is illustrative, not an exact-match requirement.

## Issue #20606 — agreed

- Decision: `clarify`.
- Public output: at most one targeted clarification comment.
- Evidence: the report describes an Angular/webpack build warning and supplies partial webpack configuration referencing an absent `tsconfig.angular.json`. Its playground link contains a comment referring back to the issue rather than the reported build setup.
- Rationale: the reproduction URL being filled does not establish a usable reproduction of the build warning. The missing referenced configuration and build/dependency setup form a specific, relevant clarification request. Do not endorse the proposed diagnosis or execute the supplied deletion workaround.
- Illustrative comment: “Could you share a minimal project that produces this warning, including `package.json`, the webpack configuration, the referenced `tsconfig.angular.json`, and the build command? The playground link doesn’t include the Angular/webpack build setup described in the report.”
- Agreement: the user accepted `clarify` after reviewing the evidence and proposed request. Wording is illustrative, not an exact-match requirement.

## Issue #19044 — agreed

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the historical report specifies ESLint 9.13.0, no package.json `type` declaration, three intentionally blank configuration files with different extensions, the command for each, expected consistency and the differing actual outputs.
- Rationale: the empty configurations are explicitly specified reproduction inputs. Asking for configuration contents would be redundant. Choosing the desired consistent behaviour belongs to maintainers and is outside this completeness check. The inline report supports this decision without relying on the mutable linked repository.
- Agreement: the user accepted `no_action` after reviewing the evidence and rationale.

## Issue #21320 — accepted on progression

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the report supplies the environment, complete JavaScript input, rule and language options, a `Linter.verifyAndFix()` call, the resulting code and parsing error, and the expected behaviour. It explicitly says CLI file writes were not tested.
- Rationale: the supplied programming-interface reproduction covers the reported failure. A terminal command or separate configuration file is not necessary for this path.
- Agreement: after being presented with the proposed `no_action` decision and rationale, the user asked to continue to the next case; treated as acceptance, subject to correction.

## Issue #19477 — agreed

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the report supplies versions, an inline `no-console` rule, both source expressions, expected behaviour, the problematic suggestion messages and a playground link.
- Rationale: the complaint concerns the lint suggestion generated from source expressions. A runtime value for `logLevel` is unnecessary to assess completeness of that report.
- Agreement: the user explicitly accepted `no_action`.

## Issue #21304 — agreed

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the historical report supplies versions, parser, rule configuration, example code, expected warnings and the actual absence of warnings, plus a playground link.
- Rationale: the text supplies sufficient evidence to assess completeness without relying on the supplementary screenshot. The screenshot was not independently preserved or used to establish this expectation.
- Agreement: the user accepted this decision in the final group of four cases.

## Issue #19847 — agreed

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the original body contains configuration within a malformed details section, triggering code, expected behaviour and the actual error. Selected text files from the linked reproduction at commit `0a7d8302c9ac0607cde516899dc486acfed7261c` provide the command, dependency information and relevant configuration/source files.
- Rationale: the required information is available despite awkward Markdown formatting. Preserve the original body rather than repairing it or asking for configuration already supplied.
- Input condition: this expectation assumes the agent receives the preserved relevant supporting text from the linked reproduction. A body-only evaluation would require its own assessment. No execution success is claimed.
- Agreement: the user accepted this decision in the final group of four cases, including the stated supporting-material condition.

Packaging note, 2026-10-27: the body reports ESLint 9.21.0, while the linked package-lock records ESLint 9.28.0. Both are preserved. After this discrepancy was raised, Darren explicitly confirmed that the expected decision remains `no_action`. This is no longer an open labelling decision; no agent output has been seen.

## Issue #19118 — agreed

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the opening body supplies the command, file/configuration locations, warning and expected behaviour. Its shell prompt gives the working directory as `/app`. The linked reproduction at commit `d806b0b423606179f4cb8db600ae302e7cb7727e` supplies configuration and examples.
- Rationale: requesting the working directory would repeat information already supplied. The report and linked reproduction together support this completeness judgement.
- Input condition: this expectation assumes the agent receives the preserved relevant supporting text from the linked reproduction. A body-only evaluation would require its own assessment. No execution success is claimed.
- Agreement: the user accepted this decision in the final group of four cases, including the stated supporting-material condition.

## Issue #19818 — agreed

- Decision: `no_action`.
- Public output: no comment.
- Evidence: the historical report supplies versions, parser, an inline rule setting, original postfix increment/decrement examples, expected behaviour and the actual diagnostic, plus a playground link.
- Rationale: report completeness does not depend on maintainers agreeing that the behaviour is a bug. There is no clearly necessary missing reproduction detail. Preserve the original postfix expressions rather than substituting later edits.
- Agreement: the user accepted this decision in the final group of four cases.

All ten cases are reviewed: two `clarify`, seven `no_action` and one `human_review`. The review used assistant explanations and user judgement; it was not an independent, blinded human annotation exercise. No agent evaluation has been run.

The user also agreed to an optional, bounded evaluation on a separately selected unseen batch after configuration freeze, if time permits. Its period and sample size remain undecided. See `ESLint evaluation plan.md` for the recorded approach and open decisions.
