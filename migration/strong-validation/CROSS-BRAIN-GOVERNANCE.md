# CROSS-BRAIN GOVERNANCE

## Global governance (centralized — must remain so)

1. **Human approval** before commercial execution
2. **MasterMind** decision packaging, escalation, tool routing
3. **AuthZ roles** (`lib/authz.ts` / `lib/auth.ts`)
4. **GL-DOS gate** (`GLDOSGovernanceGate` via `ControlledRuntimeOrchestrator`)
5. **Workflow approvals** + `EOSWorkflowEngine` transactional transitions
6. **Official evidence** fail-closed assessment
7. **Trade corridor** rules (MasterMind cannot be commercial party)
8. **Security audit** persistence for privileged writes

## Project governance (local)

Allowed locally (Egypt today; UAE/Norway when bridged):

- Read-only operational views
- Local opportunity detection / reporting
- Local inventory/supplier/shipment visibility within company mandate
- Escalation requests to MasterMind

Forbidden locally:

- Price approval, supplier activation, shipment release, payment, customs filing, self-modification (explicit in `greenyLifeEgyptBrainIdentity.prohibited`)
- Overriding MasterMind blockers
- Silent application of commercial changes

## Decision ownership

| Decision class | Owner |
|---|---|
| Cross-company trade | MasterMind → user |
| Material commercial change | Commercial change ledger + MasterMind review → user |
| Export readiness / evidence sufficiency | Evidence gates + MasterMind / export-decision agents → user |
| Local operational status (Egypt) | Egypt brain (read-only) |
| Order workflow state mutation | Workflow approvals + EOS engine (not project brains) |
| Learning promotion | Admin/learning routes + gate; no self-mod |

## Tool ownership

- Registry: MasterMind (`tool-registry.ts`)
- Local brains may request; cannot grant themselves execution power
- Legacy capabilities require adapters; `brain.py` remains reference-only

## Data ownership

- Fabric domains currently Egypt-owned for product/supplier/inventory/shipment
- Destination customer context may map to UAE/Norway companies but requires MasterMind review on mismatch
- Prisma durable tables are system-owned under authZ, not brain-owned

## Workflow ownership

- Order workflow: `/api/workflow` + `/api/workflow/approvals` + `EOSWorkflowEngine`
- Task orchestration: `/api/tasks` creates review contracts only
- Project brains do not own workflow state machines

## Escalation path

```
Local brain finding
  → MasterMind escalationReasons + approvalNotification (PENDING_USER_APPROVAL)
  → User editable decision package
  → Controlled execution only after explicit approval
  → GL-DOS / workflow approval / authorized route
```

## Cross-brain communication

**Intended:** Local brain → MasterMind (API/lib), MasterMind may later query other local brains.

**Observed today:**

- Egypt → MasterMind: yes (identity + verification harness + decision package using company IDs)
- MasterMind → UAE brain HTTP: **no** (bridge missing)
- MasterMind → Norway brain HTTP: **no** (bridge missing)
- Direct Egypt ↔ UAE/Norway brain calls: **not present**

## Forbidden authority overlaps

1. Two Main Brain executors (MasterMind + `brain.py`)
2. Project brain commercial commitment
3. Canonical JSON silently authorizing regulated export
4. Second orchestrator imported from `archive/`
5. Tool registry entries that auto-execute commercial side effects
6. GL-DOS gate returning silent AUTHORIZED for ordinary writes without durable user approval (current gate correctly returns REVIEW_REQUIRED / DENIED)
7. Brain-specific hardcodes leaking into MasterMind as unverified “facts”

## Confirmed GL-002 ↔ GL-003 conflict findings

### Conflict A — Incomplete three-brain runtime vs operating-model claim

- **Evidence:** `operatingBrains` defines three brains; only Egypt route exists; tests `three_operating_brains_check.ts` only assert metadata
- **Current authority:** Metadata claims three brains; runtime delivers one
- **Target authority:** Three local brains + MasterMind, with bridges
- **Risk:** Operators believe UAE/Norway intelligence is live
- **Recommended resolution:** Implement bridges (GL-003) or narrow operating-model API to expose `runtimeStatus: MISSING` until bridges land
- **Implementation gate:** NEEDS_HUMAN_DECISION (API honesty vs build bridges first) + NEEDS_RUNTIME_PROOF / NEEDS_TEST_PROOF for bridges

### Conflict B — Legacy Main Brain identity vs MasterMind

- **Evidence:** `brain.py` present; MasterMind routes active; safe entry blocks brain modes
- **Current authority:** MasterMind runtime
- **Target authority:** MasterMind as Main Brain; brain.py archival
- **Risk:** Agents “recover” brain.py as Main Brain
- **Recommended resolution:** Durable RAIOS decision + inventory label
- **Implementation gate:** NEEDS_HUMAN_DECISION then SAFE_TO_IMPLEMENT docs; DO_NOT_IMPLEMENT brain.py reactivation

### Conflict C — Dual orchestrator files

- **Evidence:** identical-size orchestrator in `canonical/` and `archive/old_folders/`
- **Current authority:** canonical import only
- **Target authority:** single canonical adapter
- **Risk:** future import of archive twin
- **Recommended resolution:** leave archive untouched; forbid imports (policy)
- **Implementation gate:** DO_NOT_IMPLEMENT archive promotion

### Conflict D — No duplicated MasterMind decision assembler found

- **Evidence:** single `buildMasterMindDecisionPackage` used by decision-package route
- **Status:** no active conflict
