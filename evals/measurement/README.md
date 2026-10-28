# Evidence of need — September 2026

**Two different sets of ten:** this September cohort measures observed comment activity. The separately selected historical development cases define expected agent decisions. Only #21304 and #21320 overlap; both clarification candidates, #20373 and #20606, fall outside September 2026.

## Fixed measurement

Repository: `eslint/eslint`. Creation period: **2026-09-01 00:00:00 UTC inclusive to 2026-10-01 00:00:00 UTC exclusive**. Sources were retrieved on 26 October 2026. No period extension is used to improve the result.

Query all issues with `repo:eslint/eslint is:issue created:2026-09-01..2026-09-30`. Retain `User`-authored issues whose retrieved title starts exactly `Bug:`. Include every match, regardless of current labels, outcome or apparent completeness. Exclude pull requests and Bot-authored issues.

For each issue, inspect comments created in `[issue creation, creation + 7 days)`. Deduplicate by comment ID. Confirm recovered comment count against the source's total count before applying the window.

Code a clarification request when a non-author `User` account explicitly asks the reporter for missing code, configuration, dependency/environment information, commands, logs or an accessible reproduction needed to investigate the report. Exclude bot notices, requests for product opinions, acceptance/closure messages, diagnosis and PR coordination. This measures observed requests, not whether a request was necessary.

## Results

| Measure | Result |
| --- | --- |
| All issues | 22: 17 User-authored, 5 Bot-authored |
| Eligible bug reports | 10 |
| Comments in seven-day windows | 28: 19 non-author User, 9 Bot |
| Reports with a clarification request | **0/10** |
| Time to first clarification | Undefined: none observed |
| Median time to first non-author User response | 3.3554 hours, approximately 3h 21m |

Zero clarification requests does not mean zero comments. The comment text was inspected; this is not a measurement based only on opening report bodies. The development set's two `clarify` expectations are our agreed desired decisions, not a count of observed maintainer requests in this cohort.

Issue IDs: **21293, 21295, 21304, 21314, 21319, 21320, 21321, 21356, 21361, 21368**.

## Interpretation

This month does not demonstrate a substantial clarification burden. The project remains a sandbox study of contextual judgement on occasional incomplete reports. Claim useful capability only if tests support it; do not claim proven time savings or recommend broad automatic deployment from these data.

Limits: one small month; title-prefix proxy; converted/deleted issues may be absent; retrieved titles and edited comments may differ from their original text; later requests fall outside the window. User account type does not prove unaided human authorship. Response latency measures elapsed time, not labour.

## Reproduction and audit

- `sources/september-search.json`: exact query URL, retrieval time and complete search result.
- `sources/<issue>.json`: retained public issue/timeline data. Repeat the selection and comment-window rules above on these fixed snapshots.
- `comment-coding.json`: all 28 comments, account types and coding. Coding is by the research assistant, not independent human annotation; the full text is available for checking.
- `september-results.csv`: per-report counts and first-response timestamps/latencies. Median is taken across the ten non-null first-response latencies.
- `september-summary.json`, `source-completeness.json` and `SHA256-MANIFEST.json`: definitions, totals, completeness checks and file hashes.

Keep this measurement separate from the ten purposively selected development cases and outside agent-accessible inputs. A live rerun may differ; reproduce the recorded result from the retained snapshots.

## Submission export provenance

This is a derived local export of the fixed measurement. Four expired GitHub signed-image JWT occurrences in two issue `bodyHTML` fields are redacted; plaintext reports, every comment, coding and all measured values remain unchanged. No remote image is needed for the metric. `SOURCE-SHA256-MANIFEST.json` preserves the original source hashes; `export-provenance.json` identifies redacted files and original/export hashes; `SHA256-MANIFEST.json` verifies this self-contained export. Original research files were not edited. Hashes identify omitted token bytes but cannot reconstruct them.
