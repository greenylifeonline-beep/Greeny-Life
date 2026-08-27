# HANDOFF — RAIOS-PRECANONICAL-CLOSEOUT-VERIFY-BUNDLE-02

C6_SERVICE_AVAILABLE=false. This is a C2 self-contained verification bundle, not independent verification.

## How to verify without C2 narrative

1. `git rev-parse HEAD` must equal `5ae96d04b6dca7c871ad5b836609780cc48d17ef`.
2. `git rev-parse origin/ai-evolution-202608051809` must equal the same SHA (local ref; no fetch required if already present).
3. Hash every path in `CHANGED-FILE-INVENTORY.json` and compare to `FILES-SHA256.txt` (worktree remediations are **not** in `5ae96d0`).
4. Re-run the unittest command in `TEST-RESULTS.json` if you need live reproduction; captured output is included.
5. Read bound receipt `.ai-os/receipts/command-fabric/c1c5-task/415717063d4bdd51caba7583.receipt.json` SHA256 `a289ce8e…`. First status COMPLETED. Replay recorded ALREADY_APPLIED.
6. Confirm T11 static C1 string is AUTH_FAILED in `tests/c1c5/test_dispatch.py`.
7. Confirm T41 ungranted A2A task is AUTHORITY_REQUIRED in `tests/a2a/test_auth_evidence_consistency.py`.
8. Hash C7 zip at `.ai-os/staging/rif-c7-integration/incoming/RIF-RAIOS-DONOR-PACKAGE-v1.1.zip` against `c65b671d31b4984f5e2634f2a1054383fc0cd301bb91ac1bdb2951aaca1e62db`.
9. Seat-model: glob `*SEAT-ROUTING*` should still be empty. Treat 01B collapse as unbound.

## Flags

C2_EXECUTION_PROVEN=true
C2_SELF_VERIFICATION_PROVEN=true
INDEPENDENT_VERIFICATION_PROVEN=false
C6_VERIFICATION_PENDING=true
READY_FOR_INDEPENDENT_REVIEW=true
READY_FOR_CANONICALIZATION=false
PHASE1_COMPLETE=false
WAL_WRITTEN=false
GL005_PROVEN=false
D-059=BLOCKED
HTTP_PRIMARY=true
NATS_PRIMARY=false
COMMAND_FABRIC_E2E_PROVEN=false
A2A_PRODUCTION_ACTIVATED=false
MERGE_EXECUTED=false
RESET_EXECUTED=false
SWITCH_EXECUTED=false
UNRELATED_DIRTY_FILES_PRESERVED=true

Do not treat this bundle as C6 PASS.
