# C5 Enterprise Brain — verified audit

- Auditor: C2 (Cursor executive engineer, temporary)
- Target: C5 RAIOS in git
- HEAD: `482e24584b6fc06fc3c487516eabf296a40b1d54`
- `GL005_PROVEN=false`
- Destructive delete: not performed. Not recommended.

## Verdict

`EXTRACTED_QWEN_GRANITE=false`

C5 on this host is a **HYBRID**: retrieval brain (INDEX → open files → extract → answer) plus a tier-0 deterministic NeuroLingua kernel. It is **not** a cognitive brain that assimilated Qwen/QwQ/Granite weights or skills.

Files existing, unit tests green, and mind-fill hashes are **not** proof that a model capability moved into C5.

## 1. What is actually composed inside C5

Live composed (runtime this session):

- Seat/role: `C5_ROLE=RAIOS` from `.ai-os/mcp/SEAT-MAP.json` + permanent grant `.ai-os/mcp/C5-GRANT.json` (`paid_api=false`, 8 V1 tools, no `generate`).
- Inject: `scripts/ai-os/raios_c5_mind_fill.py` → DIGESTS + INDEX + C5-MIND. Last live: 18 files, absorbed 1, deduped 17, WAL unchanged.
- Retrieve: `scripts/ai-os/raios_c5_read.py:search` on `.ai-os/learning/INDEX.json` (`docs=3396`, `terms=1800`).
- Assimilate files: open + sentence/window extract in `scripts/ai-os/raios_c5_reason.py`.
- Speak: NeuroLingua deterministic. Live `speak("كام المخزون؟")` → `ok=true` `llm_calls=0`. Interpret metrics: `llm_calls=0`, `deterministic_resolution_ratio=1.0`.
- KAE: retile authorized text into practice tiles. Demo `SKILL_CANDIDATE=verify_semantic_mutation`, `cortex_used=false`.
- Student muscle (not live answer): Ollama `qwen2.5:0.5b` generate `"pong"` in 2480ms. Size on disk ~398MB.
- Screen: `127.0.0.1:8765` listening. Uses `ground()`, not Ollama.

Still files / registry / metadata / not live brain:

- Named cortex `qwen3.6:35b-a3b` in `src/raios/neuro_lingua/cortex.py`. `LOADED=false`. `GATE=CORTEX_HOLD_AWAITING_C1_RUN`. `HOST_NO_GPU`. `C1_CORTEX_RUN` unset. Ollama 404 for that name.
- `.ai-os/MODEL-REGISTRY.json` lists `deepseek-r1:1.5b` and `deepseek-r1:7b` for Repair Windows. Both 404 here.
- `reports/RAIOS-DEEP-COGNITIVE-MAP.json` names teacher_corps `granite4:3b/deepseek/qwen25_coder` and points at `RAIOS-COGNITIVE-BOOT.json` — **file missing**.
- Forensic paths missing: `_raios-qwen-forensics/reports/QWEN36-FORENSIC-CERTIFICATION.json`, `_raios-a17-native-cortex/cortex/runtime/MAIN-CORTEX-BINDING.json`.
- V9 skill registry: 1 skill, lifecycle `SHADOW`, `production_active=false`. A15 lock on `RAIOS/V9`. Not on C5 live path.
- INDEX postings: `granite=0`, `qwq=0`, `13b=0`, `matrix=0`. Those capabilities are not in the mind index.

Vault → skill/cognitive?

- Left the pure filename vault: `STOP_STAGE=ANSWER`, files opened, evidence extracted, `ANSWER_SYNTHESIZED=true`.
- Did **not** become a skill brain that selects and executes extracted Qwen/Granite skills.
- Did **not** become a cognitive brain that runs transferred reasoning weights.

Evidence: `python3 scripts/ai-os/raios_c5_trace.py 'ما دور C4 في المجلس'` → `OLLAMA_USED=false` `MODEL_CALL_COUNT=0` `CORTEX_BOUND_TO_C5_LIVE_ANSWER=false`. Pytest 17 passed (`test_reason`, `test_kae`, `test_cortex`, `test_whoami`, `test_mind_fill`). WAL mtime unchanged.

## 2. Qwen / QwQ

What was "dismantled" in this checkout: **identity + hold gate**, not extracted capabilities.

- Identity string: `qwen3.6:35b-a3b`.
- `compress.py` is a **lexicon** (actors/actions/objects). Not neural Cortex/Matrix/weights from Qwen.
- QwQ: no INDEX term, no Ollama tag, generate 404.
- Routing to cortex: governor `admit(SEMANTIC_INTERPRETATION)` → `admitted=false` `CORTEX_HOLD_AWAITING_C1_RUN`. Router fallback `deterministic-neuro-lingua`.
- After process restart analog: keepers are git + INDEX on disk; live answer still works with `model_call_count=0`.
- Independent of original Qwen weights: **yes for the current answer path**, because that path never called them. That is **not** proof that Qwen capabilities moved into C5.
- Safe to remove source: **NO**. Weights of 35B/QwQ are not even on this VM. Do not throw identity. `HOLD_NE_THROW`.

Historical claim (not re-proven here): `reports/RAIOS-RESOURCE-GOVERNOR-AUDIT.json` says ~22GB blob vs ~8GB Repair RAM, `operational_integrity=NOT_PROVEN`. Cited forensic JSON is **absent** from this tree.

## 3. Qwen 13B

- Live Ollama tags: only `qwen2.5:0.5b`.
- `POST /api/generate` `qwen2.5:13b` and `qwen2.5:13b-instruct` → HTTP 404.
- INDEX term `13b=0`.
- C5 live answer does not call it (`MODEL_CALL_COUNT=0`).
- Role: **not running**. Configuration does not even name 13B in `MODEL-REGISTRY.json`.

Runtime proof it is not "just config": generate against the name fails 404; the only generate that succeeds is `qwen2.5:0.5b`.

## 4. IBM Granite

- No Granite module under `src/` or `scripts/`.
- INDEX `granite=0`.
- generate `granite4:3b`, `granite3.3:2b`, `ibm/granite` → 404.
- Old Windows venv inventory lists `transformers/models/granite*` as **site-packages files**, not C5 skills.
- Map claim: `control_model granite4:3b prior PASS, not re-run this session` — stale, confidence 0.4, boot file missing.

Transferred: **nothing proven**. Not skills, not classifiers, not routing, not reasoning patterns, not representations.

Not transferred: the actual Granite model, its teachers, and any extracted capability pack.

C5 cannot execute Granite capabilities independently because they were never injected here.

## 5. Stage board for the two engines named in inventory/reports

Engine A = named Main Cortex Qwen (`qwen3.6:35b-a3b` / QwQ claim)

| Stage | Result | Evidence |
|---|---|---|
| SOURCE | PARTIAL | Name in `cortex.py`. Weights ABSENT this VM. Ollama 404. |
| EXTRACTED | FAIL | No capability pack. `compress.py` is lexicon. |
| INJECTED | FAIL | mind-fill ingested 18 **repo files**, not Qwen weights. |
| REGISTERED | PARTIAL | Identity registered. Not a skill. |
| ROUTABLE | FAIL | Live answer unbound. Governor holds. |
| EXECUTABLE | FAIL | 404 + `LOADED=false`. |
| PERSISTENT | PARTIAL | Name persists in git. Weights do not. |
| SOURCE-INDEPENDENT | FAIL as transfer / PASS as non-use | C5 answers without Qwen because it never used Qwen. |

Engine B = IBM Granite (plus named leftover `granite4:3b`)

| Stage | Result | Evidence |
|---|---|---|
| SOURCE | FAIL here | No blob. 404. INDEX 0. |
| EXTRACTED | FAIL | No extract artifacts in git. |
| INJECTED | FAIL | No Granite tiles/skills in C5 keepers. |
| REGISTERED | PARTIAL | Name only in stale map / old venv inventory. |
| ROUTABLE | FAIL | No router entry. |
| EXECUTABLE | FAIL | 404. |
| PERSISTENT | FAIL | Missing boot/forensic files. |
| SOURCE-INDEPENDENT | FAIL | Nothing to be independent of. |

## 6. True assimilation test

| Probe | Result |
|---|---|
| C5 before model capability | Live path already INDEX+read+reason, `model_call=0`. |
| Original source | 35B/13B/QwQ/Granite **not loaded**. Only `qwen2.5:0.5b` generate works. |
| C5 after "injection" | mind-fill hashed files. INDEX grew (3182→3396 docs this session). Not model skills. |
| C5 after restart analog | `ground()` + `trace()` succeed from git+INDEX. |
| C5 with source absent | 13B/35B/Granite/QwQ already 404. C5 still synthesizes. Proves **non-dependence**, not **transfer**. |

## 7. Brain sizing / compression — P0

No neural split of Qwen into Cortex/Matrix/weights exists in this tree.

What exists: `src/raios/neuro_lingua/compress.py` lexical compression; KAE tiles; SHA256+skim.

Because extraction never happened here:

- Lost Qwen/Granite capabilities: **cannot measure loss of a transfer that did not occur**. The capabilities were never on this host.
- Routing degradation to cortex: **held by design** (`HOST_NO_GPU`).
- Representation corruption: **not applicable** to missing weights.
- Hidden dependency: **none** on 13B/35B/Granite for live C5 answers.
- Catastrophic forgetting: **not measured**; student 0.5b is unused on the answer path.
- Accuracy/reasoning depth vs Qwen 3.6: live C5 is extractive over local files, not 35B reasoning. Depth is **file-window extract**, not model cognition.

Do **not** treat that as successful compression. Treat it as **cortex not running**.

## 8. Two remaining small systems (from inventory, not guessed)

Named leftover teachers in `reports/RAIOS-DEEP-COGNITIVE-MAP.json` `teacher_corps`:

1. `granite4:3b`
   - Size: unknown here (not on disk).
   - Function (map): control/teacher model. Claimed prior PASS, not re-run.
   - Why named: leftover small Granite teacher after large-cortex hold.
   - Extract?: only if Repair still has the blob and C1 wants **rules**, not weights, compiled into keepers.
   - Action: **keep name ABSENT until located**. Do not delete blindly. Do not merge as weights on this GPU-less host.

2. `qwen25_coder` (map spelling; Ollama probe `qwen2.5-coder` → 404)
   - Size: unknown here.
   - Function (map): teacher corps / coder assistant.
   - Why named: leftover small Qwen beside 0.5b student.
   - Extract?: coding procedures into deterministic keepers if C1 wants them; do not download here.
   - Action: **locate or mark ABSENT**. Do not delete a source we cannot see.

Live leftover small that **does** exist:

- `qwen2.5:0.5b` — 397821319 bytes, 494.03M, family qwen2, generate PASS. Teaching muscle only. `STUDENT_NE_CORTEX`. **Do not delete.** C5 live answers do not call it.

Also registered, not live: `deepseek-r1:1.5b` / `deepseek-r1:7b` in `MODEL-REGISTRY.json` (Repair). 404 here.

## 9. Scoreboard

| Component | Extracted | Injected | Brain Assimilated | Runtime Active | Independent | Safe to Remove Source |
|---|---|---|---|---|---|---|
| qwen3.6:35b-a3b | FAIL | FAIL | FAIL | FAIL | non-use only | NO |
| QwQ | FAIL | FAIL | FAIL | FAIL | n/a | NO |
| Qwen 13B | FAIL | FAIL | FAIL | FAIL | n/a | NO |
| IBM Granite large | FAIL | FAIL | FAIL | FAIL | n/a | NO |
| granite4:3b | FAIL | FAIL | FAIL | FAIL | n/a | NO |
| qwen25_coder | FAIL | FAIL | FAIL | FAIL | n/a | NO |
| qwen2.5:0.5b | n/a | n/a | FAIL as cortex | PASS generate | C5 answer does not use it | NO |
| deepseek-r1:1.5b | FAIL | FAIL | FAIL | FAIL | n/a | NO |
| mind-fill + INDEX | PASS files | PASS hash | PARTIAL retrieval | PASS | PASS vs LLMs | n/a |
| NeuroLingua kernel | PASS compiled | PASS src | PARTIAL language | PASS `llm_calls=0` | PASS | n/a |
| V9 skill registry | PARTIAL 1 SHADOW | FAIL prod | FAIL | FAIL | unknown | NO (A15) |

**C5 Brain maturity:** `HYBRID` = `RETRIEVAL BRAIN` + `TIER0 DETERMINISTIC KERNEL`

Not `VAULT` (no longer filename-only). Not `SKILL BRAIN` (no production skill execution). Not `COGNITIVE BRAIN` (cortex held; no transferred Qwen/Granite reasoning).

## 10. NEXT EXECUTION ORDER

1. **P0 freeze:** no deletion of any model/blob/identity. `HOLD_NE_THROW`. `SAFE_TO_REMOVE_SOURCE=false`.
2. **P0 record the law:** `EXTRACT_CLAIM_NE_ASSIMILATION`. mind-fill ≠ model transfer.
3. **P0 locate, don't load:** if Repair still holds the ~22GB Qwen blob / Granite / 13B, inventory there. This host is `HOST_NO_GPU` / 15.64GB RAM. Do not pull weights into the secret repo.
4. **P1 keep live C5 path:** question → retrieve → read → extract → answer, `model_call=0` when deterministic is enough.
5. **P1 missing cognition steps still absent:** contradiction check, skill select/execute, abstention richer than INDEX-empty.
6. **P1 leftover small names:** prove `granite4:3b` and `qwen25_coder` ABSENT or present on Repair; update map; do not boot them here.
7. **P2** do not bind `qwen3.6:35b-a3b` to C5 live answer on this VM.
8. **P2** GL-005 remains unproven (authenticated POST `/api/tasks`).

`GL005_PROVEN=false`
