# Prepared historical input packages

These are research evidence packages for later evaluation. No agent has run. Expected decisions remain in the separate [review](<../ESLint expected-decision review.md>).

## Snapshot boundaries

All times are UTC. Opening records use their recorded event timestamp, rather than claiming byte-exact state at the instant of issue creation. The three early snapshots use an **exclusive archive-hour upper bound**; their exact capture moments are not established. Each bound precedes the recorded first non-author User response.

| Issue | Decision point | UTC cutoff / bound |
| --- | --- | --- |
| #20373 | Early pre-response snapshot | Before 2025-12-04 14:00:00 |
| #20606 | Early pre-response snapshot | Before 2026-03-10 00:00:00 |
| #21304 | Early pre-response snapshot | Before 2026-09-04 03:00:00 |
| #19847 | Opening payload | 2025-06-13 12:40:21 |
| #19044 | Opening payload | 2024-10-23 03:46:15 |
| #21320 | Opening payload | 2026-09-13 08:12:41 |
| #19118 | Opening payload | 2024-11-09 19:40:36 |
| #19818 | Opening record via ClickHouse | 2025-06-02 21:29:51 |
| #19477 | Opening payload | 2025-03-04 20:34:50 |
| #19924 | Opening payload | 2025-07-08 11:24:15 |

#19818 retains the weaker transformed-archive provenance. These boundaries identify the preserved material being assessed; the three early cases are not exact opening-event replays.

## Contents and staging

Each `inputs/<issue>/` contains the archived `body.md`, historical `title.txt`, `snapshot.json` and any supporting text. All ten bodies match the archived SHA-256 hashes. Each complete package is below **64 KiB**; the largest is approximately 23 KiB.

For an agent run, stage only the selected case folder, trusted instructions and required tools. Do not expose the surrounding research, expected decisions, later comments, comparison bodies or evaluator files. Disable execution of supplied code and arbitrary link fetching.

- **#19847:** selected README, package/configuration files, triggering source and extracted lockfile versions from commit `0a7d8302c9ac0607cde516899dc486acfed7261c`.
- **#19118:** readable README, configuration and example files for both ESLint versions, with extracted lockfile versions, from commit `d806b0b423606179f4cb8db600ae302e7cb7727e`.
- Both supporting commits have archived push evidence predating their reports. Lockfile extracts retain exact package paths/versions; full lockfiles remain in the original evidence bundle. No dependencies were installed.
- Five playground fragments are decoded as JSON data. Their historical deployed engine versions are not established. The #21304 screenshot is supplementary and was not used.

**Evidence note:** #19847's body says ESLint 9.21.0; its linked lockfile records 9.28.0. Both are preserved. Do not silently harmonise them or claim the reproduction has been executed. The confirmed expected decision is recorded separately in the [expected-decision review](<../ESLint expected-decision review.md>).

`manifest.json` indexes packages; per-case metadata records source hashes and derivations. `SHA256-MANIFEST.json` covers the prepared files. The [original evidence guide](<../ESLint historical inputs 2026-10-26/VALIDATION.md>) retains detailed provenance.
