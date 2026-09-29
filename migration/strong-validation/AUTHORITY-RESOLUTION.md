# AUTHORITY RESOLUTION

## MAIN BRAIN AUTHORITY

**Strongest verified candidate:** MasterMind TypeScript runtime (`lib/intelligence/mastermind-agents.ts` + `app/api/mastermind/**`).

**Role name in code:** “MasterMind AI” / “Primary decision intelligence and command authority” (`mastermindAuthority` in `lib/intelligence/three-operating-brains.ts`).

**Status:** Runtime-active decision authority — **PARTIAL formal designation** (behavior verified; organizational label “Main Brain” ≡ MasterMind still needs explicit human/RAIOS decision because `brain.py` and `intelligence/` historically compete for that label).

**Not Main Brain (verified):**

| Component | Classification | Evidence |
|---|---|---|
| `brain.py` | LEGACY / historical residue | `scripts/brain_safe_entry.py` exits 2; `tool-registry.ts` states do not import/execute |
| `intelligence/*` reports & empty stubs | Historical residue / non-runtime | No `app/` imports of `@/intelligence` |
| `ControlledRuntimeOrchestrator` | Runtime governance gate | Used by commercial-changes/learning/traceability writes; not decision packaging |
| `EOSWorkflowEngine` | Workflow executor | Order transitions under approval; not MasterMind |

## MASTERMIND ROLE

MasterMind is responsible for:

1. Assembling multi-agent read-only findings into a decision package (`buildMasterMindDecisionPackage`)
2. Escalation detection (`escalationReasons`) and approval notification (`approvalNotification`)
3. Tool routing metadata (`toolRegistry` via `/api/mastermind/tools`)
4. Operating-model exposure (`operatingBrains` via `/api/mastermind/operating-model`)
5. Commercial context summary (`commercialContextSummary`)
6. Enforcing fail-closed decision safety policy (`requireHumanApproval: true`, `automaticExecution: false`)

MasterMind is **not** responsible for:

- Silent commercial execution
- Payment / customs / title transfer
- Being a commercial counterparty (`trade-corridors.ts` / `tradeCorridorAgent`)
- Replacing project-local operational reporting

## PROJECT BRAIN AUTHORITY

Project brains are **local operational intelligence** with escalation to MasterMind.

| Brain ID | Company | Runtime authority today |
|---|---|---|
| `GREENY_LIFE_EGYPT_BRAIN` | `GREENY_LIFE_EGYPT` | Active: `lib/intelligence/greeny-life-egypt-brain.ts` + `/api/brains/greeny-life-egypt` (read-only operational view; prohibited commercial execution) |
| `GREENS_NATURE_UAE_BRAIN` | `GREENS_NATURE_UAE` | Metadata only in `operatingBrains`; **no** route/lib |
| `GREEN_LINES_NORWAY_EU_BRAIN` | `GREEN_LINES_NORWAY_EU` | Metadata + Python `greenlines_brain/` evidence source; **no** TS REST bridge |

Project brains **must not** override global MasterMind/user approval for cross-company or material commercial decisions.

## RUNTIME AUTHORITY

Executed Next.js App Router under `app/api/**` importing `lib/**` and selected `canonical/intelligence/**` / `canonical/lib/workflowEngine.ts`.

Authoritative runtime stacks:

- Decision: MasterMind routes + `lib/intelligence/*`
- AuthZ: `lib/authz.ts` + session (`lib/auth.ts`)
- Persistence: `lib/prisma.ts` + `prisma/schema.prisma`
- Write governance gate: `ControlledRuntimeOrchestrator` → `GLDOSGovernanceGate`
- Workflow mutation: `EOSWorkflowEngine.transitionOrderState` inside `prisma.$transaction`

## CANONICAL AUTHORITY

`canonical/data/**`, `canonical/inventory/**`, `canonical/logistics/**` supply read models for Egypt brain and fabrics.

`canonical/intelligence/runtime/controlled-runtime-orchestrator.ts` and `canonical/intelligence/adapters/gl-dos-governance-gate.ts` are **runtime-imported** — treat as active adapters, not mere docs.

`canonical/prisma/schema.prisma` is **non-authoritative** relative to root `prisma/schema.prisma`.

Canonical does **not** outrank MasterMind policy for execution authorization.

## POLICY AUTHORITY

Centralized and must remain centralized:

1. User approval before commercial execution
2. Role authorization (`writeRolePolicy` / `authorizeRequest`)
3. MasterMind decision safety policy
4. GL-DOS governance gate for controlled writes
5. Workflow approval consumption rules
6. Official evidence fail-closed assessment
7. Trade corridor rules that forbid MasterMind as commercial party

`governance/eos-canonical-truth-registry-v*.json` are policy/knowledge artifacts; they are **not** imported by `app/` routes in the inspected runtime graph.

## DATA AUTHORITY

| Domain | Owner (fabric) | Notes |
|---|---|---|
| PRODUCT / SUPPLIER / INVENTORY / SHIPMENT (fabric catalog) | `GREENY_LIFE_EGYPT` in `data-intelligence-fabric.ts` | Consumers include brains + MasterMind |
| Customer/commercial context | Destination-company assignment with MasterMind review | `commercial-context-fabric.ts` |
| Durable commercial proposals | Prisma `CommercialChange` | Proposal ≠ applied change |
| Official evidence | Prisma `OfficialEvidenceRegistry` | MasterMind/export agents read |

UAE/Norway operational datasets as first-class runtime owners: **UNPROVEN / incomplete** (no UAE brain lib; Norway Python not bridged).

## TOOL AUTHORITY

`lib/intelligence/tool-registry.ts` — MasterMind routes tools; tools are read-only / review dispositions; no tool overrides approval.

Source of registry knowledge includes `greenlines_brain/dna/extracted_knowledge.json` (static), not live Python execution.

## TEST AUTHORITY

Tests under `tests/` prove contracts for MasterMind, Egypt brain, operating-model metadata, GL-DOS gate, authZ, fabrics.

Passing tests prove **current** implementation behavior. They do **not** prove UAE/Norway bridges (routes absent).

DB-backed MasterMind/commercial tests require real `DATABASE_URL` (GL-004 PENDING).

## LEGACY STATUS

| Asset | Status |
|---|---|
| `brain.py` | LEGACY reference; not app runtime entry |
| `greenlines_brain/*.py` non-empty modules | EXECUTED-SOURCE / evidence engine (out-of-process); not Next bridge |
| `greenlines_brain` zero-byte placeholders | Scaffold residue |
| `intelligence/` reports & empty TS stubs | HISTORICAL / non-runtime |
| `archive/old_folders/.../controlled-runtime-orchestrator.ts` | Duplicate residue (same size as canonical; not imported by `app/`) |
| `scripts/brain_safe_entry.py` | Safety blocker for legacy modes |

## AUTHORITY FLOW

```
Local Project Brain (read-only operational view)
        │ escalate / propose
        ▼
MasterMind AI (decision package, tools, escalation, blockers)
        │ PENDING_USER_APPROVAL
        ▼
Human approval authority
        │ explicit approve
        ▼
Controlled path:
  GL-DOS gate (ControlledRuntimeOrchestrator)
  and/or WorkflowApproval + EOSWorkflowEngine transaction
  and/or authorized CRUD routes with authZ audit
        ▼
Durable state (Prisma) + audit/evidence records
```

**Forbidden inversions:**

- Project brain executing commercial commitment
- Canonical JSON authorizing export without MasterMind/evidence gates
- Runtime CRUD bypassing authZ / approval where policy requires it
- Legacy `brain.py` becoming silent Main Brain
- Multiple MasterMind-equivalent decision assemblers
