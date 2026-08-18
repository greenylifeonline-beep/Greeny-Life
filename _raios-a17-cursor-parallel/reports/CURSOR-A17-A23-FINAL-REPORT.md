# CURSOR A17.14–A23 FINAL REPORT

Isolated parallel implementation wave for live teacher-student transfer,
mastery, retirement, experience, knowledge, skill compiler, adapter factory,
elastic compute, and autonomic maintenance.

Work area: `_raios-a17-cursor-parallel/`.
No writes to live PowerShell A17.4–A17.13 paths, RAIOS/V9 canonical state, or
production stores. Qwen3.6 was not pulled or installed.

## 1. Exact files created/modified

Created (this wave only). No pre-existing files were modified.

```
_raios-a17-cursor-parallel/README.md
_raios-a17-cursor-parallel/.gitignore
_raios-a17-cursor-parallel/manifest/WAVE-MANIFEST.json
_raios-a17-cursor-parallel/integration/NATIVE-CORTEX-BRIDGE.json
_raios-a17-cursor-parallel/schemas/Experience.schema.json
_raios-a17-cursor-parallel/schemas/KnowledgeDebt.schema.json
_raios-a17-cursor-parallel/schemas/KnowledgeObject.schema.json
_raios-a17-cursor-parallel/schemas/Skill.schema.json
_raios-a17-cursor-parallel/schemas/TrainingCandidate.schema.json
_raios-a17-cursor-parallel/schemas/TransferGraph.schema.json
_raios-a17-cursor-parallel/schemas/VerifierResult.schema.json
_raios-a17-cursor-parallel/src/raios_parallel/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/__main__.py
_raios-a17-cursor-parallel/src/raios_parallel/identity.py
_raios-a17-cursor-parallel/src/raios_parallel/models.py
_raios-a17-cursor-parallel/src/raios_parallel/transitions.py
_raios-a17-cursor-parallel/src/raios_parallel/store.py
_raios-a17-cursor-parallel/src/raios_parallel/cli.py
_raios-a17-cursor-parallel/src/raios_parallel/runtime.py
_raios-a17-cursor-parallel/src/raios_parallel/ingest.py
_raios-a17-cursor-parallel/src/raios_parallel/auditor.py
_raios-a17-cursor-parallel/src/raios_parallel/transfer_graph.py
_raios-a17-cursor-parallel/src/raios_parallel/migrations/001_initial.sql
_raios-a17-cursor-parallel/src/raios_parallel/governance/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/live_learning/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/semantic_validation/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/verifier/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/mastery/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/retirement/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/experience/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/knowledge/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/rkg/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/skills/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/distillation/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/scheduler/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/maintenance/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/cortex/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/context/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/memory/__init__.py
_raios-a17-cursor-parallel/src/raios_parallel/adapter/__init__.py
_raios-a17-cursor-parallel/tests/test_parallel_a17_a23.py
_raios-a17-cursor-parallel/tests/certify_cursor_a17_a23.py
_raios-a17-cursor-parallel/tests/CERTIFY-CURSOR-A17-A23.ps1
_raios-a17-cursor-parallel/fixtures/teacher/valid.json
_raios-a17-cursor-parallel/fixtures/teacher/malformed.json
_raios-a17-cursor-parallel/fixtures/teacher/hash-mismatch.json
_raios-a17-cursor-parallel/fixtures/packets/teaching.json
_raios-a17-cursor-parallel/evidence/TEACHER-CAPABILITY-TRANSFER-GRAPH.json
_raios-a17-cursor-parallel/evidence/CURSOR-A17-A23-CERTIFICATION.json
_raios-a17-cursor-parallel/reports/CURSOR-A17-A23-FINAL-REPORT.md
_raios-a17-cursor-parallel/reports/CURSOR-A17-A23-MACHINE-REPORT.json
_raios-a17-cursor-parallel/reports/CURSOR-A17-A23-CERTIFICATION.json
_raios-a17-cursor-parallel/reports/UNITTEST-A17-A23.txt
```

Modified: none outside `_raios-a17-cursor-parallel/`.
RAIOS/V9 git status: clean.
`_raios-a17-native-cortex/`: absent in this checkout, not created.

## 2. Architecture

RAIOS is the organism. Identity is `raios.organism.v9`, bound read-only from
`RAIOS/V9/continuity/RAIOS-IDENTITY.json`. The Native Cortex is a replaceable
Qwen-class provider (`qwen3.6:35b-a3b` selected, not installed). Cortex output
is always a proposal. RAIOS governance owns execution and canonical promotion.

Isolated runtime: filesystem CAS + SQLite metadata + hash-chained `audit_events`
WAL + FTS5. Large experience blobs are stored in CAS, not SQLite.

| Scope | Implementation |
| --- | --- |
| A17.14 | `LiveStudentEngine`: BASELINE → FREEZE → TEACHER_EXPOSURE → PRACTICE → UNSEEN_TRANSFER → RETENTION → INDEPENDENT_VERIFICATION. Contamination token hidden during baseline/transfer. MASTERED impossible without all evidence. |
| A17.15 | Semantic verifier: DETERMINISTIC / STRUCTURAL / TEST_EXECUTION; MULTI_MODEL / HUMAN / FRONTIER return PENDING. Lexical overlap is not authority. Teacher may be wrong; student may outperform. |
| A17.16 | 10-dimension mastery + default thresholds. CLI: evaluate, status, teacher-dependency, capability-gap, retention-status, transfer-status. Scalar scores are insufficient (`mastery_scalar_insufficient=true`). |
| A17.17 | Capability-specific retirement. Never deletes. Unique capability / transfer / retention / regression / evidence / teacher dependency block retirement. |
| Transfer graph | Teacher → Capability → Lesson → Skill → Transfer Test → Student Evidence → Mastery → Retirement State |
| A18 | ExperienceStore: append/get/query/search/link/replay_candidate/compress_candidate |
| A19 | KnowledgeObject lifecycle DISCOVERED…VALIDATED; CANONICAL requires governed promotion. KnowledgeDebt is a separate entity; reading does not pay. |
| RKG | Controlled node/relation set with deterministic IDs |
| A20 | SkillCandidate → ValidatedSkill pipeline; no auto-activate |
| A21 | Adapter/distillation contracts; no training unless isolated test data; no auto-promote |
| A22 | Provider SPI + scheduler + GPU_VALUE_PER_MINUTE; GPU jobs with no measurable gain fail closed; no paid setup |
| A23 | Maintenance observe/diagnose/quarantine/repair-candidate/rollback-candidate + degraded modes. Identity survives every mode. |
| Context compiler | Budget, ranking, contradiction preservation, exclusion manifest |
| MemorySPI | put/get/search_text/search_vector/neighbors/link/health; RAIOS remains authority |
| ModelProvider SPI | discover/health/load/unload/infer/structured_infer/tool_plan/context_limits/resource_requirements/adapter_attach/detach |
| Bridge | Read-only discovery of `_raios-a17-native-cortex` reports: FOUND / MISSING / PENDING / BLOCKED |
| Reality auditor | Anti-self-deception inventory; never invents harvest truth |

Shared cognitive state is one identity + Memory, Knowledge, RKG, Experience,
Skills, Policies, Learning, Competency, Evidence. No per-agent canonical memory.

## 3. Reuse vs new code

Reused (read-only / imported, not duplicated authorities):

- `_raios-a17-integration-wave` — organism identity primitives + CAS
- `RAIOS/V9/continuity/RAIOS-IDENTITY.json` — identity bind
- `RAIOS-COGNITIVE-LEARNING-FABRIC-REFERENCE-V2` — debt/training/differential contracts
- `RAIOS-SHARED-COGNITIVE-EXCHANGE-REFERENCE-V2` — CAS + SQLite + hash-chain WAL pattern

New: isolated `_raios-a17-cursor-parallel` package.

## 4. Tests

Command:

```bash
python3 -m unittest discover -s _raios-a17-cursor-parallel/tests -v
```

Result: **35 tests, OK**.

The 30 required cases plus extras:

1. malformed teacher artifact quarantined
2. hash mismatch rejected
3. duplicate input idempotent
4. teacher self-report remains unverified
5. teacher may be wrong
6. student may outperform teacher
7. unseen transfer hidden from teacher content
8. baseline frozen before teaching
9. mastery impossible without transfer
10. mastery impossible without retention
11. mastery impossible without independent verification
12. capability-specific retirement
13. unique teacher capability blocks retirement
14. deletion never automatic
15. validated != canonical
16. rejected promotion does not mutate state
17. model output cannot execute tools directly
18. context budget enforced
19. contradictions preserved in context
20. experience lineage preserved
21. knowledge provenance preserved
22. training candidate requires validation
23. skill candidate cannot auto-activate
24. adapter cannot auto-promote
25. identity survives cortex replacement
26. provider failure enters degraded mode
27. SQLite integrity
28. WAL integrity
29. idempotent retries
30. rollback boundaries preserved

Extras: knowledge-debt reading cannot pay; GPU without gain blocked;
lexical overlap is not authority; reality audit does not invent harvest;
transfer graph shape.

Certification:

```bash
python3 _raios-a17-cursor-parallel/tests/certify_cursor_a17_a23.py
```

Windows child: `tests/CERTIFY-CURSOR-A17-A23.ps1`.
`WAVE_CERTIFICATION=PASS` with persisted-state inspection and negative-control
failure reasons.

## 5. PASS / FAIL / PENDING

| Claim | Status |
| --- | --- |
| A17_14_LIVE_LEARNING_ENGINE | PASS |
| A17_15_SEMANTIC_VERIFIER | PASS |
| A17_16_MASTERY_ENGINE | PASS |
| A17_17_RETIREMENT_ENGINE | PASS |
| A18_EXPERIENCE_PLANE | PASS |
| A19_KNOWLEDGE_PLANE | PASS |
| A20_SKILL_COMPILER_FOUNDATION | PASS |
| A21_ADAPTER_FACTORY_CONTRACT | PASS |
| A22_ELASTIC_COMPUTE_CONTRACT | PASS |
| A23_MAINTENANCE_CONTRACT | PASS |
| UNIT_TESTS | PASS |
| WAVE_CERTIFICATION | PASS |
| A17.4 teacher harvest (this checkout) | MISSING / PENDING_RUNTIME_VALIDATION |
| A17.5 assimilation (this checkout) | MISSING / PENDING_RUNTIME_VALIDATION |
| A17.6–A17.13 live PowerShell outputs | MISSING / PENDING_RUNTIME_VALIDATION |
| Main Cortex installed | false (not authorized here) |
| Main Cortex bound | false |
| Mastered capability count | 0 |
| Canonical mutation count | 0 |

Laptop-reported A17.4/A17.5 PASS numbers were **not** copied into this checkout
and are **not** claimed here.

## 6. Unresolved dependencies

- Completed active PowerShell A17.6–A17.13 output
- Local `_raios-a17-native-cortex` harvest tree
- qwen3.6:35b-a3b installation / disk capacity
- Real GPU / paid providers
- Human authorization for canonical promotion, teacher deletion, model delete
- MULTI_MODEL / HUMAN_REVIEW / FUTURE_FRONTIER_TEACHER verifier providers

## 7. Collision / safety ledger

- PowerShell collision avoided: writes confined to `_raios-a17-cursor-parallel/`
- Qwen runtime state: not installed, not pulled
- Teacher state: constitution lists three temporary teachers; presence in this checkout is PENDING (harvest root absent)
- RAIOS/V9 before: unmodified
- RAIOS/V9 after: unmodified
- commit (canonical / harvest / V9): false
- push (canonical / harvest / V9): false
- model delete: false
- fake mastery: false

## 8. Next recommendation

1. Let the live PowerShell A17.6–A17.13 path finish without interruption.
2. Point `RAIOS_A17_NATIVE_ROOT` at the completed harvest and re-run
   `reality-audit` (read-only).
3. Ingest A17.4/A17.5 observations into this isolated store; keep verification
   UNVERIFIED until the live student engine produces transfer + retention +
   independent verification.
4. Only then evaluate mastery / retirement. Do not retire teachers because
   Qwen3.6 is larger or disk is tight.
5. Qwen3.6 load remains a separate, authorized step.
