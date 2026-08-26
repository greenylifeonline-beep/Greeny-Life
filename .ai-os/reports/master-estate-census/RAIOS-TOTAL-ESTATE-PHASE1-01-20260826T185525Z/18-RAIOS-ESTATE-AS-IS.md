# RAIOS estate as-is — Phase-1 closeout

HOST=AG  
RUN=RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z  
TASK=RAIOS-TOTAL-ESTATE-PHASE1-02  
TREE-001 HEAD=`12603d02253547c7727bc84ce68c318e8e9258bc`  
PHASE1_COMPLETE=false  
READY_FOR_PHASE2=false

## What exists (authoritative surface count)

Master registry: 71 surfaces (`S01`–`S71`). The competing total **61** is `STALE_REPORT` from run `RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T1853Z` (incomplete write before Desktop/C3 extras and `S71`). Do not replace 71.

Fourteen Kaggle logical classes are registered as `S57`–`S70`. **S58 KAGGLE_NOTEBOOKS** is a surface (`KAGGLE_METADATA_OBSERVED_BY_C1`) with two child assets `KAG-NB-001` and `KAG-NB-002`. That does not change `MASTER_SURFACES_TOTAL=71`.

## What runs

- C5 HTTP `:8766` PID 29160, model `qwen3:0.6b` (already-bound health evidence).
- MCP `:8788` listen; health flaky.
- NATS listen; `NATS_PRIMARY=false`.
- Ollama listen; **11** installed tags described; only `qwen3:0.6b` bound as C5 cortex.

## What each important class is, and what should happen

| System | What it is | What should happen |
|---|---|---|
| TREE-001 Repair | Current dirty canonical candidate | Keep. Do not reset/merge/fetch. |
| Retired clone | Independent donor git | Keep as REFERENCE/DONOR. |
| C5 + USER-ROUTER + CHANNEL | Live local cognitive path | Keep runtime / canonical. |
| MCP / Ollama / NATS | Live engines | Keep; NATS stays non-primary. |
| S35 nomadic PRE_LLM | Draft C6 package, 10 hashed files | Inventory only. `REUSE_CANDIDATE`. Do not promote. |
| GL-002 | Historical implementation (branch + closeout docs + archive status) | Do not reconstruct. Missing worktree ≠ missing capability. |
| GL-003 | Evidence-only (archive status; no current source tree) | Do not reconstruct. |
| CICF 1464 tools | Statically classified; 46 P0 empty/garbage only | Reuse P2 `IMPLEMENTS`/`SUPPORTS`. Do not delete. |
| Kaggle S58 notebooks | C1 UI: 2 exist; content not bound | Do not infer Git/content |
| Kaggle other classes | UNRESOLVED + blocker | No fake inventory |
| origin/main `da67f449` | GitHub Kaggle-labeled notebook commit | GitHub-side observation only. Not a Kaggle push proof. |

## Cloud scope (independent flags)

`PUBLIC_GITHUB_READ_ACCESS_PROVEN=true` from `git ls-remote`.  
Private GitHub, Cursor Cloud, Kaggle, OneDrive content, and other cloud: **false**. Do not collapse these into generic `CLOUD_ACCESS_PROVEN`.

## C6

C6 is `OFF_HOST_EVIDENCE_RECONCILER`. `C6_AG_ACCESS_PROVEN=false`. `C6_RECONCILIATION_FROM_HANDOFF=true`. Off-host copies are not AG access.

## Must not touch

No delete/merge/fetch/hydrate/GPU/C5 restart. Do not promote WAL, GL-005, NATS, Qwen/Granite extraction, or S35.
