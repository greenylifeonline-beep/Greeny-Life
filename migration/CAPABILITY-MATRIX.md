# System Capability Matrix

This matrix classifies the major enterprise capabilities identified in the Greeny-Life platform. It defines the current status of each capability, its operational alignment, and the action plan required for complete consolidation.

## Classification Definitions
*   **KEEP:** Retain the target implementation verbatim.
*   **MERGE:** Combine legacy logic and updated target code, preserving state and resolving structural conflicts.
*   **MIGRATE:** Actively translate legacy modules, data, or scripts into modern target patterns.
*   **REPLACE:** Overwrite legacy code entirely with a new, robust target equivalent.
*   **ARCHIVE:** Keep purely read-only historical files for preservation/traceability.
*   **DELETE-CANDIDATE:** Deprecated or redundant systems identified for removal.
*   **UNPROVEN:** Legacy capabilities that lack execution proof, runtime callers, or test validation.

---

## Strategic Capability Breakdown

### 1. Main/Master Intelligence Brain
*   **Core Systems:** `brain.py` (legacy vs target), `lib/intelligence/three-operating-brains.ts`
*   **Classification:** **MERGE**
*   **Current State:** The legacy single-file Python brain is extremely dense (~318KB) and handles a wide range of tasks (audit scanning, remediation, opportunities, reporting). In Codex, this file has been slightly modified and checked into the root. However, its architectural authority has been moved to the modular Next.js REST API layout and TypeScript libraries.
*   **Next Steps:** Gradually decompose remaining Python business algorithms into TypeScript adapters inside `lib/intelligence`.

### 2. Three Project-Specific Brains
*   **Core Systems:**
    *   *Greeny-Life Egypt Brain:* `app/api/brains/greeny-life-egypt/route.ts`, `lib/intelligence/greeny-life-egypt-brain.ts`
    *   *Greens Nature UAE Brain:* Conceptualised in `THREE-OPERATING-BRAINS.md` and referenced in `lib/intelligence/three-operating-brains.ts`.
    *   *Green Lines Norway/EU Brain:* Pythonic modules under `greenlines_brain/`.
*   **Classification:**
    *   *Egypt Brain:* **KEEP** (Already fully operational in Next.js TypeScript with comprehensive unit testing).
    *   *UAE Brain:* **UNPROVEN / MIGRATE** (No dedicated router or logic file exists in Codex yet. Data must be extracted from `brain.py` hardcoded sections).
    *   *Norway Brain:* **MERGE** (Python modules are preserved in the root, but TypeScript REST integration is missing).
*   **Next Steps:** Code the REST endpoints and specialized TS handlers for the UAE and Norway brains under `app/api/brains/` and `lib/intelligence/`.

### 3. Governance and Orchestration
*   **Core Systems:** `governance/`, `lib/intelligence/workflow-governance.ts`, `app/api/mastermind/operating-model/`
*   **Classification:** **KEEP**
*   **Current State:** Fully implemented. Governance registries (`eos-canonical-truth-registry-v3.json`) and Next.js policy deciders are synchronized.

### 4. Canonical Knowledge
*   **Core Systems:** `canonical/` data directories, `GREENY-LIFE-EOS-KNOWLEDGE-BASE-V1/`
*   **Classification:** **KEEP**
*   **Current State:** Replicated completely in the Codex workspace. File integrity and schema layouts have been maintained.

### 5. Intelligence Systems
*   **Core Systems:** `intelligence/` (comprehensive AST reports, AST raw files, deep clean logs)
*   **Classification:** **KEEP**
*   **Current State:** Legacy reports are fully stored and indexed inside `intelligence/`. No further copying needed.

### 6. Application, Domain, and Database Layers
*   **Core Systems:** `application/`, `domain/`, `database/`
*   **Classification:** **KEEP**
*   **Current State:** VERIFIED. Identical structures in both directories. The business logic matches.

### 7. APIs and Runtime Routes
*   **Core Systems:** `app/api/` folder structure
*   **Classification:** **REPLACE**
*   **Current State:** Legacy API was limited to CRUD operations on four tables. Target Next.js Next API routes are substantially broader, adding auth, audit logging, mastermind controllers, task queues, and brain REST routing.

### 8. Prisma / Schema / Migrations / Data Models
*   **Core Systems:** `prisma/schema.prisma` vs `canonical/prisma/schema.prisma`
*   **Classification:** **REPLACE**
*   **Current State:** The legacy basic schema was replaced by the upgraded schema in root `prisma/`, which integrates 9 robust enterprise models (such as `TradeTraceRecord`, `CommercialChange`, `OfficialEvidenceRegistry`, and `WorkflowApproval`).
*   **Next Steps:** Run database migrations in Target to realize the schema upgrade.

### 9. Workflow and Decision Engines
*   **Core Systems:** `lib/intelligence/workflow-approval.ts`, `app/api/workflow/`
*   **Classification:** **KEEP**
*   **Current State:** Target has transitioned legacy status updates into a fail-closed transactions architecture utilizing `WorkflowApproval` database models and cryptographic `correlationId` tracking.

### 10. Agents and Agent Orchestration
*   **Core Systems:** `MASTERMIND-AGENTS.md`, `lib/intelligence/mastermind-agents.ts`
*   **Classification:** **KEEP**
*   **Current State:** Explicit agent definitions (Evidence, Product, Trade Corridor, Traceability, System Learning) are hardcoded as pure-composability TypeScript classes in `lib/intelligence/mastermind-agents.ts`.

### 11. GL-DOS
*   **Core Systems:** `src/gl_dos/`
*   **Classification:** **MIGRATE**
*   **Current State:** GL-DOS is the legacy Command-Line interface wrapper. It is referenced in `canonical/system_manifest.json` as a module, but its core logic lives in `src/gl_dos/` (Python/JS).
*   **Next Steps:** Establish a clean Next.js dashboard/shell wrapper or Node-based CLI command runner in target.

### 12. GELS (Greeny-Life Egypt Labeling/Packaging System)
*   **Core Systems:** `lib/intelligence/gels-label-readiness.ts`, `tests/gels_label_readiness_check.ts`, `data/03_packaging_system.json`
*   **Classification:** **KEEP**
*   **Current State:** Ported completely to Next.js TypeScript, utilizing `gels-label-readiness.ts` to execute label audits and layout constraints dynamically.

### 13. EOS Intelligence
*   **Core Systems:** `eos-core/`
*   **Classification:** **KEEP**
*   **Current State:** Replicated verbatim.

### 14. Knowledge Systems
*   **Core Systems:** `KNOWLEDGE-BASE/`, `GREENY-LIFE-EOS-KNOWLEDGE-BASE-V1/`
*   **Classification:** **KEEP**
*   **Current State:** Replicated safely in Target.

### 15. Tests and Runtime Evidence
*   **Core Systems:** `tests/` directories
*   **Classification:** **REPLACE**
*   **Current State:** Legacy had only performance test scripts. Codex features 48+ highly comprehensive TypeScript testing specs proving fail-closed behaviors, authorization layers, mastermind constraints, and data integrity.
