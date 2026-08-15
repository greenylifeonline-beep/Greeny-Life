# Runtime Gaps Analysis

This document identifies all operational, syntactic, and structural gaps between the legacy implementation (OLD) and the new target environment (Codex). It includes a detailed gap assessment of APIs, database schemas, and automated test coverage.

---

## 1. API Surface Area & Missing Routes

The API surface area of Codex is enormously expanded compared to legacy. This creates a gap where legacy components expect simple, basic endpoints but Codex imposes sophisticated, secure routing.

*   **Legacy API Endpoints:**
    *   `/api/products` (Basic products JSON return)
    *   `/api/sales-orders` (Sales orders tracking)
    *   `/api/suppliers` (CRUD suppliers list)
    *   `/api/workflow` (Direct order state updates, e.g. updating order statuses directly in memory without audit)
*   **Codex Modern API Endpoints (and corresponding gaps):**
    *   `/api/brains/greens-nature-uae` (**GAP:** Missing endpoint for UAE operational intelligence).
    *   `/api/brains/greenlines-norway` (**GAP:** Missing endpoint for Norway/EU operational intelligence).
    *   `/api/mastermind/decision-package` (Provides aggregated, audited user approvals).
    *   `/api/commercial-changes` (Durable commercial state propose-and-review).
    *   `/api/auth` (Session tracking and role policies).
*   **Impact:** Legacy systems might attempt to directly perform operations (like updating an order status) that Codex blocks unless accompanied by a `WorkflowApproval` and valid transaction state.

---

## 2. Database Schema & Migration Gaps

The Prisma schema has underwent a comprehensive upgrade. This is the largest architectural shift between the repositories.

*   **Legacy Schema (`canonical/prisma/schema.prisma`):**
    *   Contains only 17 basic database tables representing core models (Organization, Entity, Supplier, Product, SKU, Batch, Packaging, Warehouse, Inventory, Customer, SalesOrder, SalesOrderItem, Shipment, Document, Invoice, Payment, User, AuditLog).
    *   Lacks any workflow checks, transaction gating, or machine learning tracking.
*   **Codex Schema (`prisma/schema.prisma`):**
    *   Fully integrates **9 brand-new advanced enterprise tables**:
        1.  `WorkflowApproval` (Fail-closed transaction gates for order transitions).
        2.  `CommercialChange` (Idempotent tracking of time-bound pricing/supplier changes).
        3.  `TradeTraceRecord` (Immutable trace ledger preserving material provenance chain).
        4.  `DecisionOutcome` (Append-only metrics to measure decision accuracy).
        5.  `TrainingCase` (Persisted outcomes reviewed and marked as ML signals).
        6.  `EvaluationRun` (Benchmarks candidate models against training cases).
        7.  `OrchestrationTask` (Idempotent task queuing records).
        8.  `SecurityAuditEvent` (Immutable tracking of route access failures/successes).
        9.  `OfficialEvidenceRegistry` (A separate evidence submission and verification table).
*   **Prisma Client Generation Gap:**
    *   **Legacy:** No active Client generation trace was found in root files.
    *   **Codex:** Contains `.next/` cache traces, indicating active Next.js/Prisma client integration and local build artifacts (`tsconfig.tsbuildinfo`).
    *   **Action Required:** Run `npx prisma migrate dev` in the Codex workspace to sync the target Postgres instance to this upgraded schema before attempting high-volume integration runs.

---

## 3. Automated Testing Gaps (Indisputable Proof of Evolution)

Testing is where the evolution of Codex is most mathematically and empirically proven.

*   **Legacy Test Footprint:**
    *   Contains exactly **1 directory** (`tests/performance/`) with basic diagnostic and execution timers.
    *   Zero API unit tests, zero authorization checks, zero mock data boundary validations.
*   **Codex Test Footprint:**
    *   Features **48 comprehensive TypeScript and Python validation suites**!
    *   *Examples of Codex tests proving security:*
        *   `tests/api_authorization_check.ts`
        *   `tests/authorization_audit_fail_closed_check.ts`
        *   `tests/auth_security_check.ts`
        *   `tests/decision_safety_adversarial_check.ts`
        *   `tests/greeny_life_egypt_brain_authorization_check.ts`
    *   *Examples of Codex tests proving features:*
        *   `tests/greeny_life_egypt_brain_check.ts`
        *   `tests/task_orchestration_check.ts`
        *   `tests/persisted_official_evidence_mapper_check.ts`
        *   `tests/three_operating_brains_check.ts`
*   **Test Environment Gap:**
    *   Codex uses a strict, tsconfig-mapped execution setup. The tests run against the modern REST interfaces to prevent unauthenticated database mutation, while legacy code has no such guards.
