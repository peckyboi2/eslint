# Packaging verification records

The first packaging-test run is retained in `verifier-tests-initial.txt`. It reported one error and one failure: the historical safety suite was run in parallel in the source checkout while the packaging tests copied it. Three synthetic adversarial-preview fixture directories appeared during that copy. The complete-tree verifier correctly rejected the unexpected additions.

The 172 historical safety tests themselves passed. Those newly generated records were labelled synthetic infrastructure, had no public actions, and made no model or provider call. They were moved to a disposable directory outside the submission; no original retained run or evidence file was changed or removed.

The current `python3 -B scripts/verify_submission.py --safety-tests` entry point first verifies the complete source checkout, then runs the unchanged historical suite inside a disposable local clone/copy. The new tests verify that this leaves every source-checkout file and byte unchanged. Current results are in `verifier-tests.txt`, `safety-tests.txt` and `verification.json`; their separate `SHA256-MANIFEST.json` covers these logs and this note. All checks are offline.
