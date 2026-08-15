# Migration Waves Blueprint

This document divides the remaining consolidation tasks into large, safe, and independently verifiable execution waves. Each wave assigns non-overlapping write scopes to specialized agents to maximize throughput while avoiding merge conflicts.

---

## Concurrency Governance & Safety Model

To prevent file collision and race conditions:
1.  **Strict Scope Isolation:** No two agents may have write locks on the same directory during the same wave.
2.  **Shared State Validation:** All agents must commit their work, verify it compiles, and update the global RAIOS state in `.ai-os/state/CURRENT-STATE.json` and `.ai-os/state/TASKS.json` before handing off.
3.  **Core Directory Lock:** Only one agent at a time may edit root configuration files (such as `package.json`, `tsconfig.json`, `prisma/schema.prisma`).

---

## Wave Plan & Agent Allocation Matrix

```
       [WAVE 1: Brain APIs]       -->     [WAVE 2: Integration]      -->     [WAVE 3: Final Verification]
  ├─ Claude: UAE Brain Implementation     ├─ Gemini CLI: GL-DOS CLI Wrapper  ├─ GitHub Agent: CI Run / Linting
  ├─ Cursor: Norway Brain TS Bridge        ├─ DeepSeek: Legacy Docs Cleanup   ├─ Codex: Schema Migration Execution
  └─ ChatGPT: MasterMind UI Logic         └─ Claude: Core Database Seeds     └─ Cursor: Final Fixes
```

---

### Wave 1: Local Brain REST Endpoints & MasterMind Orchestration
*   **Objective:** Eliminate the gap for UAE and Norway/EU local brain APIs and wire them into the MasterMind decision orchestrator.
*   **Agent Allocations:**
    *   **Claude Code:**
        *   *Scope:* `app/api/brains/greens-nature-uae/`, `lib/intelligence/greens-nature-uae-brain.ts`
        *   *Task:* Implement UAE brain and data layers using hardcoded assets parsed from legacy `brain.py`.
    *   **Cursor:**
        *   *Scope:* `app/api/brains/greenlines-norway/`, `lib/intelligence/greenlines-norway-brain.ts`
        *   *Task:* Create TypeScript REST bridge for the Norway brain. Read Python `greenlines_brain/` modules using safe execution or direct translation.
    *   **ChatGPT Main Brain:**
        *   *Scope:* `app/api/mastermind/decision-package/`
        *   *Task:* Enhance mastermind orchestrator to query UAE and Norway endpoints concurrently during package aggregation.
    *   **Gemini CLI (me):**
        *   *Scope:* `tests/` (excluding other scopes)
        *   *Task:* Create new TypeScript tests for UAE and Norway brains (`tests/greens_nature_uae_brain_check.ts`, `tests/greenlines_norway_brain_check.ts`) to ensure fail-closed boundary validations work.
*   **Verification Gate:** Run all tests in `tests/` verifying all three operating brains respond correctly with 100% type safety.

---

### Wave 2: Legacy Command Integration (GL-DOS) & Core Seeds
*   **Objective:** Re-establish terminal operations (GL-DOS CLI) inside the Codex Next.js structure and seed the database using canonical JSON sources.
*   **Agent Allocations:**
    *   **Gemini CLI (me):**
        *   *Scope:* `scripts/gl-dos/`
        *   *Task:* Build a robust Node-based CLI runner wrapping legacy `src/gl_dos` routines, utilizing the new Next REST APIs rather than direct DB calls.
    *   **Claude Code:**
        *   *Scope:* `prisma/seeds/`
        *   *Task:* Create seed scripts parsing `canonical/data/*.json` and loading them via Prisma client to the database.
    *   **DeepSeek:**
        *   *Scope:* `archive/docs/`
        *   *Task:* Scan all legacy `.md` and `.txt` files in `canonical/docs/`, clean formatting anomalies, and copy relevant architectural documents to Codex read-only folders.
*   **Verification Gate:** Run seed scripts successfully; verify that querying `/api/products` retrieves seeded canonical records.

---

### Wave 3: Final Schema Migrations & Full CI Validation
*   **Objective:** Run the Postgres database migrations, compile the entire Next.js application, and run the test suite inside CI.
*   **Agent Allocations:**
    *   **Codex:**
        *   *Scope:* Root directory (`prisma/`)
        *   *Task:* Execute database migrations (`npx prisma migrate dev --name init_expanded_repair_schema`).
    *   **Cursor:**
        *   *Scope:* Root workspace (`tsconfig.json`, compilation errors)
        *   *Task:* Address any Next.js runtime build errors arising from type mismatches.
    *   **GitHub Agent:**
        *   *Scope:* `.github/workflows/`
        *   *Task:* Run full CI linting (`npm run lint`), compilation (`npm run build`), and test execution (`npm run test`).
*   **Verification Gate:** Green build output, 100% passing rate on automated test suites under Node.js runtime.
