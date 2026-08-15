# OLD → CODEX Migration Map

This document establishes the official and authoritative mapping between the legacy repository (`C:\Users\Ghanam\OneDrive\projects\Greeny-Life`) and the Codex target repository (`C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair`).

## Directory-Level & System Mapping

| Legacy Path (OLD) | Codex Target Path | Classification | Content Type Classification | Description / Alignment Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `app/api/products` | `app/api/products` | **KEEP** | ACTIVE RUNTIME | Core CRUD endpoints for product management. Kept intact in Codex with updated Next.js routing. |
| `app/api/sales-orders` | `app/api/sales-orders` | **KEEP** | ACTIVE RUNTIME | Sales order tracking and creation API. Kept intact. |
| `app/api/suppliers` | `app/api/suppliers` | **KEEP** | ACTIVE RUNTIME | Supplier integration and CRUD endpoints. Kept intact. |
| `app/api/workflow` | `app/api/workflow` | **MERGE** | ACTIVE RUNTIME | Ported to Codex with enhanced verification and audit log capabilities. |
| (None - New) | `app/api/brains` | **KEEP** | ACTIVE RUNTIME | New Next.js REST routing framework for localized brains (e.g. `greeny-life-egypt`). |
| (None - New) | `app/api/mastermind` | **KEEP** | ACTIVE RUNTIME | New mastermind API including `commercial-context`, `decision-package`, `operating-model`, and `tools`. |
| `application/` | `application/` | **KEEP** | EXECUTED SOURCE | Core business application service layers (customer, inventory, logistics, product, quality, supplier). Kept verbatim. |
| `domain/` | `domain/` | **KEEP** | EXECUTED SOURCE | Pure domain model layer (entities, validations, invariants). Kept verbatim. |
| `canonical/` | `canonical/` | **KEEP** | CANONICAL KNOWLEDGE | Contains master data stores. Kept and extended (e.g., `system_manifest.json` updated with reformatting and slight adjustments). |
| `canonical/prisma/schema.prisma` | `prisma/schema.prisma` | **REPLACE** | ARCHITECTURE / SPEC | Legacy basic Postgres schema replaced by root `prisma/schema.prisma` with 9 additional advanced models (`WorkflowApproval`, `CommercialChange`, etc.). |
| `brain.py` | `brain.py` | **MERGE** | ACTIVE RUNTIME / EXEC | Single-file legacy enterprise operating brain (~318KB). Retained in Codex root (~320KB) with subtle updates; logic is being incrementally refactored into TypeScript. |
| `greenlines_brain/` | `greenlines_brain/` | **MERGE** | EXECUTED SOURCE | Norway/EU-specific modular Python intelligence. Codex retains Python source but introduces empty modules/scaffolding to prepare for TypeScript wrappers. |
| `governance/` | `governance/` | **KEEP** | CANONICAL KNOWLEDGE | PowerShell validation script and canonical JSON truth registries. Kept verbatim. |
| `tests/performance/` | `tests/performance/` | **KEEP** | TEST EVIDENCE | Legacy performance tests. Kept verbatim. |
| (None - New) | `tests/*` (45+ files) | **KEEP** | TEST EVIDENCE | Brand-new TypeScript automated testing suite covering all API endpoints, authorization checks, and fail-closed security. |
| `_GREENY_DIAGNOSTIC_...` | `_GREENY_DIAGNOSTIC_...` | **ARCHIVE** | HISTORICAL MATERIAL | Diagnostics generated during system transitions. Retained for traceability. |
| `E3-RECON-OUTPUT/` | `E3-RECON-OUTPUT/` | **ARCHIVE** | HISTORICAL MATERIAL | Core outputs and evidence packages from historical E3 audits. |
| `E3-SOURCE-TRACE-PACKAGE/` | `E3-SOURCE-TRACE-PACKAGE/` | **ARCHIVE** | HISTORICAL MATERIAL | Zip files and text manifests of E3 source traces. |
| `.next/`, `node_modules/` | (None - Generated) | **DELETE-CANDIDATE** | GENERATED POLLUTION | Build outputs and temporary dependencies. Strictly ignored. |

---

## Detailed Content Classification Schema

### 1. ACTIVE RUNTIME IMPLEMENTATION
*   **Definition:** Code files and configurations that actively execute in the production environment of the Next.js runtime.
*   **Key Files in Codex:** `app/api/**/*.ts`, `lib/intelligence/**/*.ts`, `prisma/schema.prisma`, `app/layout.tsx`.
*   **Status:** Strictly verified, audited, and fully integrated with fail-closed security policies.

### 2. EXECUTED SOURCE (PYTHON / LEGACY ENGINE)
*   **Definition:** Standalone engines (e.g. `brain.py`, `greenlines_brain/*`) that were run out-of-process in legacy, but are being systematically phased into Next.js.
*   **Key Files in Codex:** `brain.py`, `greenlines_brain/kernel.py`, `greenlines_brain/graph.py`.
*   **Status:** Preserved as-is in the root directory for dual-run trace verification.

### 3. ARCHITECTURE / SPECIFICATION
*   **Definition:** Schema definitions, markdown architectural constraints, and configuration limits.
*   **Key Files in Codex:** `THREE-OPERATING-BRAINS.md`, `INTELLIGENCE-RUNTIME-POLICY.md`, `ASSET-ASSIMILATION-POLICY.md`.
*   **Status:** Authoritative; governs all runtime adapters and agent tasks.

### 4. CANONICAL KNOWLEDGE
*   **Definition:** Immutable JSON datasets, truth registries, and product portfolios that define corporate data truth.
*   **Key Files in Codex:** `canonical/**/*.json`, `governance/eos-canonical-truth-registry-v3.json`.
*   **Status:** Replicated in target with no loss of structural integrity.

### 5. TEST / EXECUTION EVIDENCE
*   **Definition:** Automated check files, output dumps, and performance indicators that prove runtime health.
*   **Key Files in Codex:** `tests/*.ts`, `tests/*.py`, `E3-GIT-STATUS.txt`, `FileSummary.csv`.
*   **Status:** Massively expanded on Codex side (from 1 folder in legacy to 48 comprehensive TypeScript validation specs).

### 6. HISTORICAL / ARCHIVE MATERIAL
*   **Definition:** Diagnostic traces, old backups, decision logs, and zip files preserved strictly for structural integrity and reference.
*   **Key Files in Codex:** `archive/`, `_GREENY_DIAGNOSTIC_20260809_233236/`, `GreenyLifeEOS_Review.zip`.
*   **Status:** Kept as read-only and preserved safely in the repository.

### 7. GENERATED / BUILD / CACHE POLLUTION
*   **Definition:** Ephemeral build directories, package manager caches, and local IDE configurations.
*   **Key Files:** `.next/`, `node_modules/`, `tsconfig.tsbuildinfo`.
*   **Status:** Excluded from the migration map. Must never be staged or committed.
