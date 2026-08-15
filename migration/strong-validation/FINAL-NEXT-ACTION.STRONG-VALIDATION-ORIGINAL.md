# FINAL NEXT ACTION

## Minimal ordered plan

### Step 1 — Smallest safe next implementation action (after this validation)

**Action:** In the **GL-003 project-brains worktree** (`raios/gl-003-project-brains`), implement the **Egypt-pattern UAE brain scaffold only after human data-source decision**, OR if human defers data: add an explicit `runtimeStatus: "MISSING"` for UAE/Norway on `/api/mastermind/operating-model` via coordinated GL-004/GL-002 change.

**Preferred smallest code action (once human chooses data path):**

1. Human decides UAE data source (canonical extract vs blocked).
2. GL-003 implements:
   - `lib/intelligence/greens-nature-uae-brain.ts` (read-only identity + operational view)
   - `app/api/brains/greens-nature-uae/route.ts` (authZ mirror of Egypt)
   - `tests/greens_nature_uae_brain_check.ts` + authorization check

**If human has not decided UAE data:** do **not** invent distributors from `brain.py`. Next action becomes documentation-only honesty about MISSING bridges (still not GL-005).

### Step 2 — Task / worktree ownership

| Action | Owner worktree / task |
|---|---|
| Formal “Main Brain = MasterMind” decision | Human + GL-002 (`intelligence`/`governance` docs/decisions only) |
| UAE/Norway bridges | GL-003 worktree |
| Operating-model honesty / route wiring | GL-004 if touching `app/`; GL-003 for brain libs |
| Real DB proof | GL-004 with provisioned `DATABASE_URL` |
| Convergence orchestration | GL-005 only after gates below |

### Step 3 — Required validation for Step 1 bridge work

- Type-check / build lists new routes
- Egypt-pattern authorization test PASS for UAE
- `three_operating_brains_check` still PASS
- MasterMind still does not auto-execute
- No imports of `brain.py`
- Scope locks: do not write GL-002-locked governance/intelligence simultaneously without unlock coordination

### Step 4 — What remains blocked

1. Norway TS bridge (needs bridge-strategy human decision)
2. MasterMind live aggregation of three brains
3. GL-002 VERIFIED (residue + naming)
4. GL-004 real DB suites
5. GL-005 unified orchestrator

### Step 5 — Exact condition before GL-005 convergence

GL-005 may become **CONDITIONALLY_READY** only when **all** are true:

1. Durable decision recorded: Main Brain authority = MasterMind TS path; `brain.py` = LEGACY  
2. UAE bridge classification = **VERIFIED** (route + lib + tests)  
3. Norway bridge classification = **VERIFIED** or explicitly **DEFERRED** with operating-model honesty and accepted risk sign-off  
4. GL-004 real `DATABASE_URL` integration proof = **PASS** for MasterMind/commercial/verification DB suites  
5. Strong validation re-run shows GL-002 ≥ PARTIAL→improving to VERIFIED checklist closed, GL-003 ≥ PARTIAL with bridges addressed  
6. No new dual decision-assembler or project-brain execution authority introduced  

Until then: **GL-005 = NOT_READY**.

## Do not do next

- Do not implement GL-005 now
- Do not execute legacy runtime
- Do not “dedupe” 52 basename hits
- Do not reactivate `brain.py` as Main Brain
