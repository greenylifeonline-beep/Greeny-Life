# Brain System Inventory

This document maps and inventories the primary intelligence systems of the Greeny-Life platform. It outlines the core orchestration files, localized operational engines, current gaps, and migration requirements.

---

## 1. MasterMind AI (Main Intelligence Brain)

*   **Legacy Implementation:** `brain.py` (~318KB)
    *   *Path:* Root of OLD and Codex target repositories.
    *   *Role:* Acts as the Complete Autonomous Enterprise Brain. Operates on a loop executing filesystem scanning, linting, remediation code, Excel/CSV audit parsing, and daily reporting.
    *   *Capabilities Found:*
        1.  `ScanResult` and `RemediationResult` data classes.
        2.  File checksum validation and deep file integrity checks.
        3.  Automated fix scripts (imports cleanup, formatting, indentation correction).
        4.  Excel / CSV master ledger loading (e.g., parsing products, suppliers, tracking data).
        5.  Context rehydration from `.json` reports to Python data structures.
*   **Codex Modern Implementation:** `lib/intelligence/mastermind-agents.ts` & `app/api/mastermind/*`
    *   *Role:* Decision-only orchestrator. It executes no code changes or commercial transactions. It strictly aggregates analysis across five specialist agents (Evidence, Product, Trade Corridor, Traceability, System Learning) and produces an editable decision package.
    *   *Security Pattern:* Fail-closed. All decisions are `PENDING_USER_APPROVAL`.
*   **Alignment Strategy:** Preserve legacy `brain.py` as a historical, run-on-demand audit utility. All active runtime decision-making, context separation, and compliance verification are fully ported to the Next.js API endpoints under `/api/mastermind/*` and TypeScript files under `lib/intelligence/`.

---

## 2. Greeny-Life Egypt Brain (Project Brain #1)

*   **Status:** **FULLY MIGRATED & VERIFIED**
*   **Codex Locations:**
    *   *REST API Endpoint:* `app/api/brains/greeny-life-egypt/route.ts`
    *   *Business Logic Layer:* `lib/intelligence/greeny-life-egypt-brain.ts`
    *   *Automated Tests:* `tests/greeny_life_egypt_brain_check.ts`, `tests/greeny_life_egypt_brain_authorization_check.ts`
*   **Capabilities Realized:**
    *   *Read-Only Operational View:* Exposes Egyptian product portfolios, warehouse definitions (Cairo, Alexandria), stock alerts, unverified suppliers, and shipment trails.
    *   *Escalation Decider:* If cross-company trade, new markets, regulatory exceptions, or price changes are requested, it escalates to MasterMind AI.
    *   *Test Proof:* Verified by `tests/greeny_life_egypt_brain_check.ts` demonstrating correct mock boundary assertions (using `canonical/inventory/stock-levels.json`).

---

## 3. Greens Nature UAE Brain (Project Brain #2)

*   **Status:** **UNPROVEN / GAP**
*   **Legacy Source Data:** Hardcoded structures inside legacy `brain.py`:
    *   *GCC Countries Segment:* `["UAE", "Saudi Arabia", "Kuwait", "Qatar", "Bahrain", "Oman"]`
    *   *GCC Suppliers/Distributors:* `"Al Baraka Trading" (Dubai)`, `"Al Jazeera Import-Export" (Abu Dhabi)`, `"Dubai Organic Market" (Dubai)`
    *   *GCC Target Ports:* `"PORT-GCC-DXB" (Jebel Ali Port)`
*   **Codex Locations:**
    *   *REST API Endpoint:* `app/api/brains/greens-nature-uae/route.ts` (**MISSING**)
    *   *Business Logic Layer:* `lib/intelligence/greens-nature-uae-brain.ts` (**MISSING**)
    *   *Automated Tests:* `tests/greens_nature_uae_brain_check.ts` (**MISSING**)
*   **Migration Plan:**
    1.  Create `lib/intelligence/greens-nature-uae-brain.ts` modeled directly on `greeny-life-egypt-brain.ts`.
    2.  Extract the GCC supplier and port metadata from `brain.py` (lines 2036-2057) and hardcode them as static records inside the UAE brain library.
    3.  Create Next.js endpoint `app/api/brains/greens-nature-uae/route.ts` to expose the local operational view.
    4.  Add unit testing in `tests/` asserting correct UAE brain boundary behaviors and MasterMind escalation rules.

---

## 4. Green Lines Norway/EU Brain (Project Brain #3)

*   **Status:** **PARTIALLY MIGRATED (SCRAPING/PYTHON PRESERVED, REST API GAP)**
*   **Legacy Source Data:** Complete Python framework inside `greenlines_brain/` folder in root:
    *   `kernel.py` (Deals with institutional memory, short-term vs long-term, confidence weights).
    *   `graph.py` (Maintains knowledge graph node structures).
    *   `identity.py` (Entity scopes, European compliance models).
    *   `ontology.py` (Semantic types).
    *   `contract.py` (Interfaces for AskResult and Evidence).
*   **Codex Locations:**
    *   *Python Engine:* Preserved safely under `greenlines_brain/` in target root.
    *   *REST API Endpoint:* `app/api/brains/greenlines-norway/route.ts` (**MISSING**)
    *   *Business Logic Layer:* `lib/intelligence/greenlines-norway-brain.ts` (**MISSING**)
    *   *Automated Tests:* `tests/greenlines_norway_brain_check.ts` (**MISSING**)
*   **Migration Plan:**
    1.  Since the Python code in `greenlines_brain/` contains high-fidelity institutional memory and confidence algorithms, retain it in Python.
    2.  Create a TypeScript wrapper/bridge inside `lib/intelligence/greenlines-norway-brain.ts` that either interfaces with `greenlines_brain/` via subprocess spawning or cleanly translates its core rulesets into equivalent TypeScript.
    3.  Add REST endpoint `app/api/brains/greenlines-norway/route.ts` allowing mastermind API integration.
    4.  Verify via automated check files in `tests/`.
