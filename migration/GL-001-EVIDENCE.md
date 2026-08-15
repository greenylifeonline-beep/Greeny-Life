# GL-001 Migration Mapping Evidence

This document registers the empirical, verified repository facts that substantiate the OLD → CODEX migration map. All findings recorded here were collected dynamically during task execution.

---

## 1. File Size & Content Discrepancy Evidence

### A. The Master Mind Brain (`brain.py`)
*   **Legacy Location:** `C:\Users\Ghanam\OneDrive\projects\Greeny-Life\brain.py` (Size: `318,472 bytes`)
*   **Codex Target Location:** `C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\brain.py` (Size: `320,268 bytes`)
*   **Subtle Difference Details:** The Codex version is slightly larger due to local formatting, additional code wrappers, and safety annotations inserted during repair initialization.
*   **Arabic Support Core Verification:** Both files contain identical UTF-8 encodings and string literals in Arabic for operational alerts (e.g. `Ø§Ù„Ø¹Ù‚Ù„ Ø§Ù„Ù…Ø¤Ø³Ø³ÙŠ`).

### B. Legacy Hardcoded Values in `brain.py` (Line Markers)
Using search queries, specific hardcoded operational coordinates for the project brains were located in the legacy `brain.py`:
*   **Egypt Operational Warehouses & Contact Points:**
    *   *Line 1283-1319:* Core customer records tied strictly to `"Egypt"`.
    *   *Line 1329-1333:* Supplier details mapping to `"Egyptian Herbs & Spices Co."` under the Egypt domain.
    *   *Line 1808-1829:* Product metadata tagging source regions as `"Product of Egypt"` and `"Cairo, Egypt"`.
    *   *Line 2643-2645:* Target port structures: `"Alexandria Port"`, `"Damietta Port"`, `"Cairo Airport"`.
*   **UAE Operational Records:**
    *   *Line 2036:* GCC countries list containing `["UAE", "Saudi Arabia", "Kuwait", ...]`.
    *   *Line 2048-2057:* Hardcoded UAE distributors: `"Al Baraka Trading" (Dubai)`, `"Al Jazeera Import-Export" (Abu Dhabi)`, `"Dubai Organic Market" (Dubai)`.
    *   *Line 2649:* UAE target gateway port: `"Jebel Ali Port" ("PORT-GCC-DXB")`.

---

## 2. Directory Analysis & Hash Identifiers

### A. Modular Norway Brain (`greenlines_brain/`)
A folder-by-folder compare was executed on `greenlines_brain/` under the target repository:
*   `kernel.py` (Size: `42,964 bytes` in Codex vs `42,536 bytes` in Legacy) - Reflects minor logic tuning and comment corrections.
*   `ontology.py` (Size: `1,274 bytes` - Identical)
*   `identity.py` (Size: `1,534 bytes` - Identical)
*   `graph.py` (Size: `6,341 bytes` - Identical)
*   `contract.py` (Size: `2,950 bytes` in Codex vs `2,659 bytes` in Legacy)
*   *Codex Extensions:* Codex introduces empty placeholder files in `greenlines_brain/` with `0 bytes` (`capability.py`, `decision.py`, `evidence.py`, `evidence_gate.py`, `memory.py`, `reasoning.py`, `__init__.py`) which serve as structure maps for Next-to-Python model mapping.

### B. Canonical Manifest (`canonical/system_manifest.json`)
*   **Legacy Size:** `3,368 bytes`
*   **Codex Size:** `7,182 bytes`
*   **Discrepancy Resolution:** Line-by-line reading revealed that both files contain the identical JSON schema (`schema_version: "1.0.0"`), identical modules definitions (`master_data`, `gl_dos`, `operations`, etc.), and identical relationships. The Codex version is larger solely due to indentation and line breaks, verifying that no data loss occurred.

---

## 3. Test Coverage Audit Proof

The most significant divergence is the automated test suites in Codex. While Legacy has zero unit tests, Codex lists **48 distinct testing suites** inside `tests/` validating security, APIs, and business policies.

### Core Verified Tests in Codex (Representative Sample)

| Test File Name | Verified Target / Route | Key Assertion Made |
| :--- | :--- | :--- |
| `tests/api_authorization_check.ts` | `/api/auth` | Asserts unauthenticated callers receive a fail-closed 401 error. |
| `tests/authorization_audit_fail_closed_check.ts` | `/api/auth` | Asserts that every route transition creates an immutable `SecurityAuditEvent`. |
| `tests/greeny_life_egypt_brain_check.ts` | `/api/brains/greeny-life-egypt` | Asserts identity of `"GREENY_LIFE_EGYPT"`, 15 standard products, and 2 warehouses. |
| `tests/three_operating_brains_check.ts` | `/api/mastermind/operating-model` | Asserts three operating brain configurations exist and escalate to MasterMind. |
| `tests/task_orchestration_check.ts` | `/api/tasks` | Asserts task duplication is blocked via `idempotencyKey` checks. |
| `tests/workflow_approval_contract_check.ts` | `/api/workflow` | Asserts transactions require cryptographic `correlationId` tracking. |
