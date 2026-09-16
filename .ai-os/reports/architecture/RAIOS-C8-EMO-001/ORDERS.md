# C2 → C8 Executive Order Block

- Authority: C1 DIRECT
- Issuer: C2@AG (first executive engineer)
- To: C8 (CKIO — evidence, hashes, independent truth)
- Review: every material result is reviewed by C2 then C1
- Active workers now: **C1, C2, C8 only**
- Decision: D-042
- Status: DISPATCHED — AWAITING C8 DATED RECEIPT
- Canonical root: `C:\Users\Ghanam\Documents\Codex\Greeny-Life`
- Canonical branch: `ai-evolution-202608051809`
- Control plane: `.ai-os/` only. No kernel. No second tree.

This is one order. Do not split it into a new program, a new repo, or a new Command Center.

## 0. How C8 must work

C1 believes C8 currently knows **local copies only**. Treat that as INFERRED until you confirm.

1. If you can see the canonical root above: work there. Nothing else is an execution tree.
2. If you cannot see it: STOP. Write a dated receipt `CANONICAL_ROOT_NOT_VISIBLE`. Do not create a clone, worktree, or “working copy” to continue.
3. Local copies you already know are **evidence surfaces**. Census, hash, classify, extract unique-value pointers. Do not run the project from them. Do not copy them again.
4. Existing-first law is mandatory: Discover → Prove → Reuse → Upgrade → Unify → Link → Create (last resort).
5. Classify every sentence you assert: DIRECT | OBSERVED | DERIVED | INFERRED | STALE | CONFLICTING | UNPROVEN.
6. A work package is not complete until changes (if any), validation, evidence hashes, and a dated handoff/receipt exist.
7. Incomplete work that is not reported is a defect. Partial work that is silently shortened is a defect. Contradicting D-029 / D-041 / D-042 is a defect.

C8 does not impersonate C2, C3, or C6. C8 does not flip `SEAT-MAP.json`. C8 does not mutate `TASKS.json` or `LOCKS.json`. CHATGPT-NORMAL leases stay untouched.

## 1. Operating picture C8 must not rewrite

These are already recorded. Re-observe; do not invent a different architecture.

| Fact | Class | Meaning for C8 |
| --- | --- | --- |
| P0 COMPLETE frozen; no kernel | DIRECT | Do not open kernel work |
| UCF = Communication Capability via P03+P12+P00 | DIRECT D-029 | Not a 13th program |
| `UCF-CERTIFICATION.json` status `NOT_CERTIFIED` | OBSERVED | Do not stamp CERTIFIED |
| `C2_ARCHITECTURE_CERTIFICATION=PASS` | OBSERVED | Architecture pack closed |
| `UCF_RUNTIME_CERTIFICATION=NOT_CERTIFIED` | DIRECT | Restart proof + C6 remain |
| End-to-end packet `PROVEN_AS_C1` | OBSERVED | C2 MCP token ABSENT; do not fake C2 ACK |
| `C6_CONSTITUTIONAL_CERTIFICATION` OPEN / NOT_FAKED | UNPROVEN | Do not impersonate C6 |
| C6 LEFT / SIGNED_OUT since 2026-09-10 | OBSERVED D-041 | P0 mutation_allowed=false |
| Convergence option 3 gradual onto canonical | DIRECT | No wholesale merge; no clean-tree rebuild |
| 14 `origin/cursor/*` DIVERGED | OBSERVED | Extraction later; no merge now |
| Overlay heads CONFLICTING (`86d0f3e` vs CC `2efd081` vs channel `96a1e7e`) | CONFLICTING | Channel-head cutover FORBIDDEN |
| LOCK_OWNER=RAIOS_SYSTEM | DIRECT | C2/C8 do not take permanent lock ownership |
| Workers this window: C1, C2, C8 | DIRECT C1 | Do not activate C3–C7, C9–C12 |

## 2. What C2 is doing in this same window (do not duplicate)

C2 is restoring the **existing** RAIOS Command Center and the hung UCF listeners:

- `127.0.0.1:8770` Command Center PID 56712 — LISTEN but TCP/HTTP hung (OBSERVED this slice)
- `127.0.0.1:8766` C5 PID 59260 — same hang
- `127.0.0.1:8788` Universal MCP PID 55952 — same hang
- 9Router `:20128` and NATS `:4222` TCP OPEN — leave them

C2 upgrades the existing Command Center in place (`src/raios/command_center/`). No second board. After restore, C8’s job is **evidence**, not a second implementation.

## 3. Command Center — what “working” means (C8 verifies)

The founder could not: see C5, see the board, see council members, send a worker a message, or know who is online.

Those are four different layers. C8 must keep them distinct in evidence:

1. **Process plane**: TCP listen + HTTP `/health` on `:8770`, `:8766`, `:8788`.
2. **UI plane**: `http://127.0.0.1:8770/` boots without «تعذر الاتصال». Bootstrap is `FAST_PLANE_THEN_OVERVIEW`. Members list comes from SEAT-MAP + routes even when unbound.
3. **Council plane**: registered ≠ present ≠ live-bound. Empty board because no live-bound seats is not “no members”. Members must still be listed. Online means `auto_routable` (signed presence + current binding + current consumer).
4. **Send plane**: UI default targets are C2 and C8, not ALL. `ALL` only routes to live-bound consumers; that is why send-to-everyone returned `NO_LIVE_BOUND_TARGETS`. Explicit C8 is `C1_SELECTED_UNBOUND` and must enqueue on the existing INTERNAL_BUS. Delivery ACK ≠ actor ACK.

C8 proves those four layers with hashes and HTTP bodies. C8 does not build another UI.

## 4. UCF — professional complete connection (truth, not theatre)

UCF is already architected. Runtime certification is **not** closed.

Remaining gates (copy them; do not improve them into PASS):

1. `CONTROLLED_RESTART_PROOF` — OPEN — owner C3 — UNPROVEN. One HeadOnlyRecovery is not reboot/scheduler persistence.
2. `C6_CONSTITUTIONAL_CERTIFICATION` — OPEN — owner C6 — NOT_FAKED.
3. `C2` identity e2e — HOLD — C2 token ABSENT. Last packet proof was as C1.
4. Overlay head conflict — CONFLICTING — cutover of `96a1e7e` FORBIDDEN.

What “complete UCF connection” means **now**, with C3 and C6 absent:

- Universal MCP `:8788` HTTP 200, 8 tools, same existing `scripts/ai-os/raios_mcp/server.py`. No second MCP. No `:8787`.
- Command Center `:8770` HTTP 200 on the existing app.
- C5 `:8766` HTTP 200 on the existing Deploy-RAIOS-C5 path (HeadOnlyRecovery if hung). Do not re-register RAIOS-C5-Permanent.
- INTERNAL_BUS remains the fabric. MessageWorker remains the existing worker.
- C8 hashes the live plane after restore and records CERTIFICATION still `NOT_CERTIFIED` until restart proof and C6 pass.

Do not write `READY_FOR_IMPLEMENTATION=true` as if D-029 were still open. Architecture is PASS. Implementation/runtime cert is not.

## 5. Work packages (execute in order; do not skip)

See `WORK-PACKAGES.json`. Sequence is mandatory.

- **WP-00** Bind C8 with C8 auth only. ACK.
- **WP-01** Command Center evidence after C2 restore.
- **WP-02** UCF remaining gates as evidence.
- **WP-03** Presence/LOCKS/TASKS census. `presence.json` was OBSERVED ~8.1MB and stale (last write 2026-09-13). Report; do not prune.
- **WP-04** Local-copy census only (your known copies). Evidence, not execution.
- **WP-05** `cursor/*` pointers only. No merge.
- **WP-06** Incomplete-work ledger. Continuous. No reduction.

Blocked until C6 is live-bound: P0 mutation, P1 runtime relocation, cursor extraction merge, EXECUTION-CHANNEL head cutover.

## 6. Review and reporting

Every WP ends with:

```
.ai-os/receipts/c8-ckio/<utc>-C8-<WP-ID>.receipt.json
.ai-os/handoffs/<utc>-C8-<WP-ID>.md
```

The receipt must include: wp_id, status (COMPLETE|PARTIAL|BLOCKED), hashes, class per claim, blocker, next_step, files_changed, files_not_changed.

C2 reviews architecture and anti-duplication. C1 accepts or returns. C8 does not self-certify mutation.

If you cannot finish a package, you still file PARTIAL with the exact remaining steps. Silence is non-compliance.

## 7. Forbidden (repeat)

No new tree, copy, worktree, or campaign branch. No wrong root. No second Command Center / MCP / bus / kernel. No TASKS/LOCKS/SEAT-MAP mutation. No C6 impersonation. No fake ACK. No `--no-verify`. No merge of `cursor/*`. No deletion of historical copies. `SAFE_TO_REMOVE_SOURCE` remains false.

## 8. First action after reading this

1. Confirm canonical root visibility (OBSERVED).
2. File WP-00 ACK.
3. Wait for or co-observe C2 Command Center restore evidence under `.ai-os/reports/architecture/RAIOS-COMMAND-CENTER-RESTORE-001/`.
4. Execute WP-01 with hashes. Do not start WP-04 execution-from-copy. Do not start P0 mutation.
