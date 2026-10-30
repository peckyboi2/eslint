# Stop workflow evidence — 30 October 2026

Original logs, exact stop-evidence artifacts, run/job metadata and a read-only post-run state snapshot are preserved here. Retrieval made no GitHub changes, dispatches, model calls or submission-repository changes. The download folder is outside eslint-fork.

## Runs

| Run | Created, Singapore time | Attempt | Result | Reported outcome |
| --- | --- | --- | --- | --- |
| [41017826713](https://github.com/peckyboi2/eslint/actions/runs/41017826713) | 30 October 2026 15:04:27 | 1 | failure | Ledger disabled; triage workflow disabled; one HTTP 403 |
| [41018317883](https://github.com/peckyboi2/eslint/actions/runs/41018317883) | 30 October 2026 15:09:09 | 1 | failure | Ledger disabled; both workflow-disable calls returned HTTP 403 |

These are two distinct manual workflow_dispatch runs, each attempt 1; the second is not GitHub attempt 2 of the first. Both used owner peckyboi2 on main at source commit e47f9920e6ba1ea5a5fdacb509d80d1f341ad5bd. The execution step returned exit code 1 and the evidence-upload step still succeeded.

## Start with these files

- [Latest stop report](41018317883/stop-evidence/stop.json): original JSON extracted unchanged from the latest artifact.
- [First stop report](41017826713/stop-evidence/stop.json): original first-run result.
- [Artifact integrity](artifact-integrity.json): both downloaded ZIP digests match GitHub metadata.
- [Post-run state summary](post-run-snapshot/snapshot-summary.json): workflow and ledger observations captured after the runs.
- [Latest full job log](41018317883/logs-attempt-1/0_stop.txt): readable logs; original logs-attempt-1.zip remains beside them.
- Per-run run-attempt-1.json, jobs-attempt-1.json and artifacts.json identify source, actor, jobs and original artifacts.

## Interpretation and limits

The returned failure is preserved as a partial stop, not relabelled a complete success. Both reports say ledger_disabled=true and workflow_disabled=false. The first reports successful triage disablement; the second reports no successful workflow-disable calls. The saved reports expose HTTP 403 but do not establish its underlying platform reason.

Both reports contain empty cancellation_requests, unresolved_runs, inflight_intents and public_actions. They support an empty scan result within the implemented scope; they do not demonstrate cancellation of running work, provider termination, device/phone operation or semantic model accuracy.

The post-run snapshot shows ledger enabled=false and posting_enabled=false. Triage and approval workflows are disabled_manually; stop and the separate manual evaluator are active. The stop scanner covers triage/approval, not the manual evaluator. This snapshot must not be described as evidence that every execution path is disabled. No workflow state was changed during evidence retrieval.

## Integrity

SHA256-MANIFEST.json preserves the initial download inventory. PACKAGE-SHA256.json covers all final package files except itself. Original ZIPs are retained alongside extracted files; no downloaded content was executed. The portable ZIP beside this directory contains the complete package.
