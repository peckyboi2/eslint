# Evaluator-only golden record

Version: `golden-v1-2026-10-27`. No evaluated agent has run.

- `prepared-inputs/`: exact copied research packages and original manifests; not per-run staging.
- `expectations.json` and `expected-decision-review.md`: accepted labels, reasons and conditions.
- `comment-quality.md`: frozen review criteria and required metrics.
- `evaluation-plan.md`: accepted sequence and sample limits.
- `FREEZE.json`: file hashes and aggregate digest, created before future evaluated inference.

Run `python3 scripts/verify_baseline.py` from the repository root to verify the freeze.
Do not edit frozen files in place. Record any justified new version separately, retain this
version and obtain human review before new evaluation. Never relabel after viewing outputs.

This directory is for Darren/evaluators only. A directory name or AGENTS instruction is NOT
an access-control boundary. Do not open this repository or its Git history in an evaluated
session. A future staging helper must export only one allowlisted historical package plus
trusted instructions to a fresh isolated environment. Exclude all evaluator documents,
measurement data, planning context, later discussions, comparisons, parent directories,
other sessions and Git metadata. Verify denied access before any evaluated run.

#19847 and #19118 must include their approved supporting text. Historical cutoff metadata,
original body bytes, both #19847 version values, and #19818's weaker transformed-archive
provenance remain unchanged. No supplied script, configuration or reproduction is executed.
The prepared-inputs README contains evaluator context and must not be staged for the agent.

Actual outputs and logs will be added only after later authorised milestones. No empty
placeholder file is a run result. This implementation chat has seen the answers and cannot
serve as an evaluated session. A coding-assistant dry run requires the same configuration
and inputs in a fresh session and must report controls it could not verify.
