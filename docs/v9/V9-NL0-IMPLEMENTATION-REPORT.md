# RAIOS V9.NL-0 — NeuroLingua Semantic Kernel

Implementation report for the first text-only NeuroLingua release.

**Claim:** NL-0 is an offline-capable language kernel integrated into Greeny-Life EOS. It is **not** production-ready as a general multilingual NLU/NLG product. Evidence below is limited to the deterministic suite (60 pytest cases, 15 seed benchmark cases). No GPU and no LLM were used.

Core rule preserved: **Model is replaceable. Meaning is canonical.**

---

## Architectural conflict (read this first)

This repository is **GREENY LIFE Digital Operating System (GL-DOS / EOS)**, not a pre-existing RAIOS V9 tree.

Reconnaissance found:

- No `Cognitive WAL`
- No `DISCOVERED → VALIDATED → CANONICAL` machine
- No NeuroLingua package, `configs/neuro_lingua/`, or `benchmarks/neuro_lingua/seed_cases.jsonl`
- No Live Brain / Evolution Brain split
- No Python capability-contract provider registry
- Host `config.yaml` pins `llm.provider: claude` — that must not become NeuroLingua architecture

**Decision (smallest compatible change):**

- Do **not** replace `GreenyLifeBrain` (`brain.py`)
- Do **not** mutate product Master Data, Prisma, or `config.yaml` (BOUND.md danger zone)
- Introduce a Python RAIOS V9 *language-layer* substrate under `src/raios/` that NeuroLingua uses
- Reuse existing GL-DOS contracts: `RiskLevel` (`LOW|MEDIUM|HIGH|CRITICAL`), capability-routing *pattern*, `intelligence/knowledge_base` path, YAML config *read*, `logs/` formatter, idempotent append (project-memory pattern)

Full map: `reports/v9-neurolingua-integration-map.json`

---

## Public API

```python
from raios import neuro_lingua

result = await neuro_lingua.interpret(text=text, context=context, target_locale=None)
rendered = await neuro_lingua.realize(meaning=result.meaning, target_locale="nb-NO", context=context)
```

`CognitiveMeaningPacket` is the Brain boundary. Callers do not select a vendor.

Pipeline:

```text
Raw Input
   ↓
Language Identification
   ↓
Dialect / Locale Resolution
   ↓
Code-Switch Segmentation
   ↓
Register + Pragmatics Analysis
   ↓
Semantic Interpretation
   ↓
CognitiveMeaningPacket
   ↓
RAIOS Brain Boundary
   ↓
Semantic Realization
   ↓
Target Locale Adaptation
   ↓
Risk-Based Verification
   ↓
Output
```

---

## Files created

### Kernel and substrate

- `src/raios/__init__.py`
- `src/raios/config.py`
- `src/raios/events.py`
- `src/raios/knowledge_state.py`
- `src/raios/observability.py`
- `src/raios/risk.py`
- `src/raios/wal/__init__.py`
- `src/raios/wal/cognitive_wal.py`
- `src/raios/providers/contracts.py`
- `src/raios/providers/registry.py`
- `src/raios/providers/local_deterministic.py`
- `src/raios/providers/llm_generic.py`
- `src/raios/neuro_lingua/kernel.py`
- `src/raios/neuro_lingua/packet.py`
- `src/raios/neuro_lingua/types.py`
- `src/raios/neuro_lingua/pipeline.py`
- `src/raios/neuro_lingua/detection.py`
- `src/raios/neuro_lingua/codeswitch.py`
- `src/raios/neuro_lingua/concepts.py`
- `src/raios/neuro_lingua/pragmatics.py`
- `src/raios/neuro_lingua/scandinavian.py`
- `src/raios/neuro_lingua/preservation.py`
- `src/raios/neuro_lingua/verification.py`
- `src/raios/neuro_lingua/realization.py`
- `src/raios/neuro_lingua/learning.py`
- `src/raios/neuro_lingua/training_policy.py`
- `src/raios/adapters/greeny_life.py`

### Config, benchmarks, tests, reports

- `configs/neuro_lingua/{config,concepts,locales,pragmatics,scandinavian}.yaml`
- `benchmarks/neuro_lingua/seed_cases.jsonl`
- `benchmarks/neuro_lingua/runner.py`
- `tests/neuro_lingua/*` (15 files)
- `pytest.ini`
- `requirements-neuro-lingua.txt`
- `intelligence/knowledge_base/neuro_lingua_manifest.json`
- `reports/v9-neurolingua-integration-map.json`
- `reports/v9-neurolingua-benchmark.json`
- `reports/v9-neurolingua-test-report.json`
- `docs/v9/V9-NL0-IMPLEMENTATION-REPORT.md` (this file)

## Files modified

- `.gitignore` — ignore `__pycache__/`, `.pytest_cache/`, `*.pyc`

**Not modified (intentionally):** `brain.py`, `config.yaml`, `src/master_data/**`, `src/finance/**`, `src/compliance/**`, Prisma, TypeScript engines.

---

## Reused existing RAIOS / GL-DOS components

| Component | Path | How reused |
|-----------|------|------------|
| Risk taxonomy | `unified-intelligence/runtime/controlled-runtime-orchestrator.ts` | Python `RiskLevel` uses the same four names |
| Capability routing pattern | `unified-intelligence/adapters/intelligence-adapter.ts` | Python `ProviderRegistry` + `NeuroLinguaCapability` |
| Knowledge-base location | `intelligence/knowledge_base/` (`brain.py` default) | WAL + evolution inbox + manifest live here |
| Idempotent append | `intelligence/memory/project-memory.ts` | WAL `event_id` skip-on-replay |
| YAML config loader pattern | `brain.py` `_load_config` | Read-only overlay of host `llm.*`; NL config is separate |
| Logging | `logs/` + brain formatter | `logs/neuro-lingua-YYYYMMDD.log` |
| Derived reports | `reports/` | NL-0 JSON reports |
| Governance BOUND | `BOUND.md` | Did not edit danger-zone paths |

---

## Decisions

1. **New WAL, not a second WAL.** None existed. JSONL local-first, no remote ACK. Canonical promotion cannot skip `VALIDATED`.
2. **Do not reuse `intelligence/core/confidence.ts`.** It returns hardcoded 100/95/85/60. NeuroLingua confidence is measured (script ratios, lexical hits). Missing tiers are listed, not scored as 0.5.
3. **Do not call an LLM by default.** Tier 0/1/2 are local. Tier 3 is eligible only when `allow_llm` and not `offline`. Default config: `offline: true`.
4. **No English pivot.** Realization uses concept-registry locale forms + preserved technical spans. If concepts are insufficient, output is a structured meaning dump (`realization_complete=false`), not a fake translation.
5. **`ar-GULF` is a parent profile.** Taxonomy includes Saudi/Emirati/Kuwaiti/Qatari/Bahraini/Omani children; classifiers are not implemented in NL-0 (`gulf_child_implemented=false`).
6. **Training is a decision path only.** `train_now` is always `False`. LoRA/QLoRA is the first *candidate* after recurrence; MoRA/MoE-LoRA/CPT are not dependencies.
7. **Back-translation is not default.** CRITICAL can request it; NL-0 skips unless explicitly enabled, and still requires an independent provider.

---

## Language profiles (NL-0)

Represented: `ar-EG`, `ar-GULF`, `en`, `nb-NO`, `sv-SE`, `da-DK`.

Egyptian vs Gulf: separate lexical profiles. Shared Arabic script does not imply a dialect; dialect confidence is `0.0` when no markers fire.

Code-switch: segments can be `ar-EG` / `en/technical` / mixed Scandinavian loans (`deploye`, `builden`, `production-databasen`). Technical identifiers are not mechanically translated.

Pragmatics: `إذا ما عليك أمر` → `politeness_marker=true`, **not** a logical condition. `الدنيا هتبوظ` → `system.regression` only when `context.domain` is in `{software, engineering, devops}`.

Scandinavian: shared understanding, isolated realizers, leakage lists for `ikke`/`inte`/`och`/infinitive markers.

---

## Benchmark results

Source: `reports/v9-neurolingua-benchmark.json` (offline, local deterministic provider).

| Metric | Value |
|--------|-------|
| Cases | 15 |
| Passed | 15 |
| Failed | 0 |
| Language detection accuracy (seed set) | 1.0 |
| Dialect detection accuracy (seed set) | 1.0 |
| Mean latency | 0.269 ms |
| LLM calls | 0 |
| Mean local execution ratio | 1.0 |

These accuracies are **seed-set** measurements, not a large held-out corpus. Do not treat them as production language-ID quality.

---

## Tests

Source: `reports/v9-neurolingua-test-report.json`

| | |
|--|--|
| Collected | 60 |
| Passed | 60 |
| Failed | 0 |
| Skipped | 0 |
| GPU required | no |
| LLM required | no |

Coverage includes: unit, contracts, golden semantic cases, code-switch, Scandinavian leakage, concept collisions, WAL replay/idempotency, offline mode, provider failure/fallback, number/entity/identifier preservation, property-based tests (Hypothesis).

Existing EOS regression:

- **Not executed here:** Vitest (`__tests__/workflowEngine.test.ts`) needs Node modules; `test_db_entities.py` needs PostgreSQL; k6 smoke needs k6.
- **Not broken by construction:** NL-0 did not modify those trees. `pytest.ini` `testpaths` is `tests/neuro_lingua` only.

---

## Remaining risks

1. Realization is **template/concept-based**, not fluent generation. Unbound utterances fall back to structured meaning.
2. Tier-1 cheap LID libraries (`langid`, `langdetect`) are optional and were **not** present in this environment; that absence is recorded, not faked.
3. Independent semantic verification for HIGH/CRITICAL is a hook; without a second provider those levels do not fully certify.
4. Gulf sub-dialects are taxonomy-only. Treating `ar-GULF` as internally homogeneous would be incorrect — NL-0 does not pretend otherwise, but it also cannot classify children yet.
5. No retrieval index exists in this repo; changing-fact routing is a *decision*, not an implemented RAG path.
6. Host `config.yaml` still names Claude. Operators could misunderstand that as NeuroLingua’s model. Routing is capability-based; the generic LLM adapter stays unconfigured by default.
7. Seed benchmark is small (15 cases). Dialect accuracy will drop on mixed/Maghrebi/Levantine input that is out of scope.

---

## What should be built in NL-1

1. Optional calibrated cheap LID (local model, no multi-GB download in CI).
2. Gulf child classifiers (SA/AE/KW/QA/BH/OM) with evidence, still parented at `ar-GULF`.
3. Independent verifier provider + optional back-translation for CRITICAL, still off by default.
4. Retrieval adapter for changing facts (reuse whatever RAG EOS grows — do not fork a second knowledge DB).
5. Richer realization (still locale-native, still no English pivot) while keeping deterministic-first routing.
6. Evolution Brain consumer of `evolution_inbox.jsonl` (compile skills; still no default training).
7. Speech/ASR/TTS — explicitly out of NL-0.
8. Wire `NeuroLinguaCapability` into a live EOS request path behind the existing governance gate.

---

## How to run (offline)

```bash
pip install -r requirements-neuro-lingua.txt
python3 -m pytest tests/neuro_lingua
python3 benchmarks/neuro_lingua/runner.py
```

No GPU. No model download. No network.
