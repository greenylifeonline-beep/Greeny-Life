# GL-003 IMPLEMENTATION GATES

## UAE / Norway bridge status (explicit)

| Required bridge | Classification | Evidence |
|---|---|---|
| `lib/intelligence/greens-nature-uae-brain.ts` | **MISSING** | Path does not exist |
| `app/api/brains/greens-nature-uae/route.ts` | **MISSING** | Path does not exist; only Egypt under `app/api/brains/` |
| `lib/intelligence/greenlines-norway-brain.ts` | **MISSING** | Path does not exist |
| `app/api/brains/greenlines-norway/route.ts` | **MISSING** | Path does not exist |
| UAE identity in `operatingBrains.GREENS_NATURE_UAE_BRAIN` | **VERIFIED** (metadata only) | `lib/intelligence/three-operating-brains.ts` |
| Norway identity in `operatingBrains.GREEN_LINES_NORWAY_EU_BRAIN` | **VERIFIED** (metadata only) | same |
| Norway Python source `greenlines_brain/` | **PARTIAL** (source present; not Next-bridged) | `kernel.py`, `evidence_gate.py`, `identity.py`, etc.; zero-byte placeholders also present |
| MasterMind HTTP fan-out to UAE/Norway brains | **MISSING** | `mastermind-agents.ts` has no `/api/brains/greens-nature-uae` or `greenlines-norway` calls |
| UAE distributors hardcoded in legacy `brain.py` | **UNPROVEN** as canonical runtime data | Mentioned in migration docs; not verified as authoritative dataset for a new brain |

Overall UAE/Norway bridges: **MISSING**.

## Per-brain validation snapshot

### 1) Greeny-Life Egypt — VERIFIED (operational)

- Identity: `greenyLifeEgyptBrainIdentity` in `lib/intelligence/greeny-life-egypt-brain.ts`
- Runtime: `app/api/brains/greeny-life-egypt/route.ts` → `greenyLifeEgyptOperationalView`
- Data: canonical products/suppliers/inventory/logistics JSON
- Tools: via shared MasterMind tool registry (not local override)
- Workflow: none owned locally; escalates to MasterMind
- Tests: `tests/greeny_life_egypt_brain_check.ts`, `tests/greeny_life_egypt_brain_authorization_check.ts`, verification harness
- Shared governance: authZ + MasterMind escalation + prohibited commercial actions
- Dependencies on Main Brain: escalatesTo MasterMind AI
- Dependencies on other brains: cross-company only via MasterMind/trade corridors

### 2) Greens Nature UAE — PARTIAL identity / MISSING runtime

- Identity metadata: present
- Runtime location: **none**
- Routes/API ownership: **none**
- Data ownership: fabric consumers listed, but no UAE-owned operational view implementation
- Tests: no dedicated UAE brain route tests found
- Bridge: **MISSING**

### 3) Green Lines Norway/EU — PARTIAL source / MISSING runtime bridge

- Identity metadata: present
- Source location: `greenlines_brain/` (Python)
- Runtime TS location: **none**
- Routes/API ownership: **none**
- Tool ownership: extracted knowledge JSON feeds tool registry statically
- Tests: `tests/test_evidence_gate.py` / legacy brain tests exist for Python evidence gate; **no** Next route bridge tests
- Bridge: **MISSING**

---

## SAFE_TO_IMPLEMENT

1. **Document-only** inventory confirming Egypt as the only verified project-brain REST implementation.
2. Create **empty scaffold files only after** human chooses data source + bridge strategy (otherwise prefer waiting).
3. Add failing/red tests that assert UAE/Norway routes are required — only if agreed as TDD gate (otherwise NEEDS_HUMAN_DECISION).

*Note:* Implementing full UAE/Norway brains is **not** SAFE_TO_IMPLEMENT without data/bridge decisions.

## NEEDS_RUNTIME_PROOF

1. Any new `/api/brains/greens-nature-uae` or `/api/brains/greenlines-norway` handler.
2. Any MasterMind change that aggregates live project-brain HTTP responses.
3. Any Python subprocess bridge from Next to `greenlines_brain`.

## NEEDS_TEST_PROOF

1. New UAE/Norway brain unit tests modeled on Egypt checks.
2. Authorization checks for new brain routes (mirror `greeny_life_egypt_brain_authorization_check.ts`).
3. Operating-model tests remaining green after brain additions (`three_operating_brains_check.ts`).

## NEEDS_DB_PROOF

1. Not required for pure read-only brain views backed by canonical JSON (Egypt pattern).
2. Required if UAE/Norway brains read Prisma commercial/evidence tables.

## NEEDS_HUMAN_DECISION

1. **UAE data source:** promote selected `brain.py` hardcodes → `canonical/data` vs rebuild from verified commercial sources.
2. **Norway bridge strategy:** TypeScript reimplementation vs controlled Python adapter vs hybrid.
3. Whether Norway `evidence_gate.py` becomes the sole evidence authority for EU corridors or remains subordinate to MasterMind official-evidence gate.
4. Ownership of GCC customer context vs MasterMind review (`commercial-context-fabric.ts` already forces review on mismatch).

## DO_NOT_IMPLEMENT

1. **Do not** invent UAE/Norway operational facts without an approved source.
2. **Do not** let project brains approve cross-company trade.
3. **Do not** execute `greenlines_brain` or `brain.py` destructively from Next.
4. **Do not** duplicate MasterMind decision packaging inside a project brain.
5. **Do not** treat migration wave plans as proof that bridges exist.

## UNPROVEN

1. UAE distributor/port records in legacy `brain.py` are complete and current.
2. Empty `greenlines_brain` modules (`decision.py`, `memory.py`, etc.) imply intended future API shapes.
3. Three project brains are “fully implemented” (false; only Egypt is).
