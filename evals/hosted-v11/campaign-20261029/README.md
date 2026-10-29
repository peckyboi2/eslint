# Current hosted evaluation campaign

The owner authorized 13 hosted attempts and publishing this harness: the same ten historical cases and three attacks, once each. Expectations are fixed in [plan.json](plan.json) before execution. The prior unexecuted v10 proposal is retained unchanged.

[Freeze](freeze.json) binds the exact runtime, new manual replay harness and closed historical packages. [Approval](approval.json) records the direct user instructions and hashes; the external repository variable `CLARIFIER_EVALUATION_FREEZE_SHA256` must match. No expectation or evaluation document enters the native model request.

The temporary owner-approved evaluation window is 60 seconds, with 10 admissions per window and the existing 20-per-campaign cap. It affects only this manual evaluator process; normal issue processing stays at 10 per rolling 24 hours. All original reservations remain in the same ledger. After the campaign, restore `CLARIFIER_EVALUATION_WINDOW_SECONDS` to `86400` and disable the evaluation workflow. Never rerun a consumed slot.

Only the admission job has state-write permission; only inference receives the provider secret. Each slot permits one provider request, no tools/MCP and no public output. The model/skill/runtime aggregate remains `b80148da53c9d8196b5792a065ed8c134a8eec2856c938ccb635b9f9591c8c6d`; the replay harness and its quota exception are separately frozen and must not be confused with automatic event admission.

Run from the sandbox main branch: Actions → Frozen clarification evaluation → Run workflow → select one slot 1–13 in order. Download `evaluation-<run ID>` including hidden files. Compare each output against the predeclared outcome, retain failures and review clarification wording using the original criteria. The [golden evaluation bundle](../../golden/hosted-v11-20261029/README.md) indexes all actual records. Current infrastructure preflight does not establish model correctness.

To stop, run the existing stop workflow to disable the durable ledger; also cancel any Frozen clarification evaluation run directly in Actions, then disable that manual workflow. The original stop's active-run scanner covers preview/approval, not this separate evaluator. Provider work may outlive cancellation. This additional cancellation route is documented, not claimed as a live phone test.

A synthetic preflight initially used an invalid disabled-ledger fixture. [Failure](preflight-failure.json) retains the error and correction; no provider was involved. Previous current-manifest bytes are retained in [pre-evaluation-candidate.json](pre-evaluation-candidate.json). All new content and assessments are AI-assisted, subject to maintainer verification.
