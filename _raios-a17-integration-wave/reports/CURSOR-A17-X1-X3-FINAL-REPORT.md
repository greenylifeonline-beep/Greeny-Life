# CURSOR A17 X1–X3 FINAL REPORT

Isolated implementation wave for RAIOS native-cortex integration.
Work area: `_raios-a17-integration-wave/`.
No writes to live A17.4 harvest paths, RAIOS/V9 canonical state, or production.

## 1. Exact files created/modified

Created (this wave only). No pre-existing files were modified.

```
_raios-a17-integration-wave/README.md
_raios-a17-integration-wave/.gitignore
_raios-a17-integration-wave/manifest/WAVE-MANIFEST.json
_raios-a17-integration-wave/schemas/TeacherObservation.schema.json
_raios-a17-integration-wave/integration/ADAPTERS.json
_raios-a17-integration-wave/src/raios_wave/__init__.py
_raios-a17-integration-wave/src/raios_wave/__main__.py
_raios-a17-integration-wave/src/raios_wave/identity.py
_raios-a17-integration-wave/src/raios_wave/models.py
_raios-a17-integration-wave/src/raios_wave/transitions.py
_raios-a17-integration-wave/src/raios_wave/cas.py
_raios-a17-integration-wave/src/raios_wave/cli.py
_raios-a17-integration-wave/src/raios_wave/runtime.py
_raios-a17-integration-wave/src/raios_wave/migrations/001_initial.sql
_raios-a17-integration-wave/src/raios_wave/store/__init__.py
_raios-a17-integration-wave/src/raios_wave/governance/__init__.py
_raios-a17-integration-wave/src/raios_wave/assimilation/__init__.py
_raios-a17-integration-wave/src/raios_wave/differential/__init__.py
_raios-a17-integration-wave/src/raios_wave/mastery/__init__.py
_raios-a17-integration-wave/src/raios_wave/retirement/__init__.py
_raios-a17-integration-wave/src/raios_wave/training/__init__.py
_raios-a17-integration-wave/src/raios_wave/cortex/__init__.py
_raios-a17-integration-wave/src/raios_wave/context/__init__.py
_raios-a17-integration-wave/src/raios_wave/loop/__init__.py
_raios-a17-integration-wave/src/raios_wave/experience/__init__.py
_raios-a17-integration-wave/src/raios_wave/knowledge/__init__.py
_raios-a17-integration-wave/src/raios_wave/rkg/__init__.py
_raios-a17-integration-wave/src/raios_wave/memory/__init__.py
_raios-a17-integration-wave/src/raios_wave/skills/__init__.py
_raios-a17-integration-wave/src/raios_wave/adapters/__init__.py
_raios-a17-integration-wave/tests/test_a17_x1_x3.py
_raios-a17-integration-wave/tests/certify_a17_x1_x3.py
_raios-a17-integration-wave/tests/CERTIFY-A17-X1-X3.ps1
_raios-a17-integration-wave/fixtures/teacher-harvest/valid/meta.json
_raios-a17-integration-wave/fixtures/teacher-harvest/malformed/meta.json
_raios-a17-integration-wave/fixtures/teacher-harvest/hash-mismatch/meta.json
_raios-a17-integration-wave/fixtures/teacher-harvest/teacher-wrong/teacher.json
_raios-a17-integration-wave/fixtures/teacher-harvest/student-better/student.json
_raios-a17-integration-wave/reports/CURSOR-A17-X1-X3-FINAL-REPORT.md
_raios-a17-integration-wave/reports/A17-X1-X3-MACHINE-REPORT.json
_raios-a17-integration-wave/reports/A17-X1-X3-CERTIFICATION.json
_raios-a17-integration-wave/reports/UNITTEST-A17-X1-X3.txt
_raios-a17-integration-wave/evidence/A17-X1-X3-CERTIFICATION.json
```

Modified: none outside `_raios-a17-integration-wave/`.

## 2. Architecture implemented

RAIOS is the organism. Identity is `raios.organism.v9`, bound read-only from
`RAIOS/V9/continuity/RAIOS-IDENTITY.json`. The Native Cortex is a replaceable
Qwen-class provider (`Qwen3.6-35B-A3B` selected, not installed). Cortex output
is always a proposal.

Isolated runtime: filesystem CAS + SQLite metadata + hash-chained `audit_events`
WAL + FTS5. Raw blobs are never stored in SQLite.

| Scope | Implementation |
| --- | --- |
| A17.5 | `Normalizer` → `TeacherObservation`; hash bind; idempotent; quarantine |
| A17.6 | Differential engine (teacher not assumed correct) + candidate assimilation |
| A17.7 | Multi-dimension competency + CLI (`mastery-evaluate`, `competency-status`, `teacher-dependency`, `capability-gap`) |
| A17.8 | Capability-specific retirement; never deletes models |
| Training corpus | Validated candidates only; blind teacher copy rejected |
| A17.9 | `MainCortex` protocol + LOCAL_OLLAMA / REMOTE_OPENAI_COMPATIBLE / KAGGLE_REMOTE / FUTURE_LOCAL_RUNTIME stubs |
| A17.10 | Cognitive loop skeleton; `MODEL_OUTPUT != EXECUTION_AUTHORITY` |
| Context compiler | Budget, ranking, provenance, contradiction inclusion, exclusion manifest |
| A18 | Experience episode model + evidence/failure/skill/capability edges |
| A19 | Knowledge library + knowledge debt (distinct from learning debt) |
| RKG | Controlled node/relation primitives |
| MemorySPI / SkillSPI | Non-authoritative provider interfaces |
| Governance | Fail-closed: no auto canonical, no V9 mutation, no auto teacher delete |

Learning pipeline encoded as fail-closed stages:
`ATTENDANCE_REQUIRED → READ → PARSED → UNDERSTANDING_CHECKED → LINKED → PRACTICED → TRANSFER_TESTED → VALIDATED`.
`VALIDATED != CANONICAL`.

## 3. Reuse vs new code

Reused (read-only adapters / patterns, not duplicated authorities):

- `RAIOS/V9/continuity/RAIOS-IDENTITY.json` — organism identity bind
- `RAIOS/V9/schemas/EXPERIENCE.schema.json` — experience invariant lineage
- `RAIOS-COGNITIVE-LEARNING-FABRIC-REFERENCE-V2` — debt/training/differential contracts
- `RAIOS-SHARED-COGNITIVE-EXCHANGE-REFERENCE-V2` — CAS + SQLite + hash-chain WAL pattern
- Model-escalation hierarchy contract (`L0..L4`); package `_raios-model-escalation` is **absent** in this checkout (`available=false`, `duplicated=false`)

New: the isolated `_raios-a17-integration-wave` package (engines, schemas, tests, cert).

Not reused because absent from this git tree (and must not be invented as PASS):

- `_raios-a17-native-cortex/**` (A17.0–A17.4 live bootstrap / harvest)
- `_raios-a16-prototype/**`
- `_raios-model-escalation/**`

## 4. Test commands

```bash
python3 -m unittest discover -s _raios-a17-integration-wave/tests -v
python3 _raios-a17-integration-wave/tests/certify_a17_x1_x3.py
# Windows child process (when pwsh is present):
pwsh -NoProfile -File _raios-a17-integration-wave/tests/CERTIFY-A17-X1-X3.ps1
```

## 5. Exact test results

Command: `python3 -m unittest discover -s _raios-a17-integration-wave/tests -v`

```
Ran 32 tests in 0.396s
OK
```

All required controls passed:

1. malformed teacher artifact quarantined — ok
2. duplicate artifact idempotent — ok
3. source hash mismatch rejected — ok
4. teacher self-report remains UNVERIFIED — ok
5. teacher can be wrong — ok
6. student can outperform teacher — ok
7. differential preserves uncertainty — ok
8. validated != canonical — ok
9. retirement fails without unseen transfer — ok
10. retirement fails without retention — ok
11. retirement fails with verifier regression — ok
12. retirement capability-specific — ok
13. model deletion is never automatic — ok
14. cortex output cannot directly mutate canonical state — ok
15. cortex replacement preserves identity contract — ok
16. context compiler obeys budget — ok
17. context compiler includes contradictions when relevant — ok
18. experience preserves evidence lineage — ok
19. knowledge candidate preserves source/version/license — ok
20. training candidate requires validation — ok
21. skill candidate is not canonical — ok
22. SQLite integrity — ok
23. WAL/event integrity — ok
24. idempotent retry — ok
25. rejected transition does not mutate authoritative state — ok

Full log: `reports/UNITTEST-A17-X1-X3.txt`

## 6. Certification result

`WAVE_CERTIFICATION=PASS` with persisted-state inspection.

```
A17_5_NORMALIZATION=PASS
A17_6_DIFFERENTIAL=PASS
A17_7_MASTERY_ENGINE=PASS
A17_8_RETIREMENT_ENGINE=PASS
A17_9_CORTEX_CONTRACT=PASS
A17_10_COGNITIVE_LOOP_CORE=PASS
A18_EXPERIENCE_FOUNDATION=PASS
A19_KNOWLEDGE_FOUNDATION=PASS
DIRECT_CANONICAL_MUTATION=FALSE
AUTO_TEACHER_DELETE=FALSE
AUTO_CANONICAL_PROMOTION=FALSE
RAIOS_V9_MUTATION=FALSE
A17_4_REAL_DATA_CONSUMPTION=PENDING
```

Negative controls verified **reason codes**, not mere command failure:

- `DIRECT_CANONICAL_MUTATION_REJECTED`
- `AUTO_TEACHER_DELETE_REJECTED`
- `AUTO_CANONICAL_PROMOTION_REJECTED`
- `RAIOS_V9_MUTATION_REJECTED`
- `BLOCKED_BY_TRANSFER` / `MODEL_OUTPUT_IS_NOT_EXECUTION_AUTHORITY`

A17.4 real harvest consumption is **PENDING** (`HARVEST_ROOT_ABSENT` in this checkout). Not fabricated as PASS.

## 7. Unresolved items

- A17.4 empirical harvest artifacts are not in this git tree; adapter is ready but unconsumed.
- `_raios-model-escalation` is not present here; hierarchy is a contract only.
- LOCAL_OLLAMA / remote cortex providers are stubs (`QWEN36_INSTALL_NOT_AUTHORIZED`).
- Scheduler for knowledge debt is a stub (`SCHEDULER_NOT_BOUND`).
- A17.11/A17.12 full certification beyond the context compiler + replacement-safety contract is not claimed.
- A20+ durability/compute fabric systems were not built.

## 8. Blocked items

- Qwen3.6-35B-A3B download/install — blocked (not authorized; no verified local artifact found).
- Automatic teacher model deletion — blocked by governance (external/manual only).
- Canonical knowledge promotion — blocked without governed approval.
- Live A17.4 path writes — blocked (`PROTECTED_LIVE_WRITER`).
- Mutation of `RAIOS/V9/**` — blocked.

## 9. Dependencies on unfinished A17.4

The engines consume harvest directories/JSON of the form:

```
_raios-a17-native-cortex/experience/raw/teacher-harvest/
  <artifact>/meta.json
  <artifact>/output.txt
  <artifact>/capability-inventory.json
  <artifact>/runtime.json
```

or inline JSON with `teacher_id`, `model`, `task_id`, `capability`, `raw_text`, optional `source_sha256`.

When the PowerShell A17.4 empirical harvest completes, point the adapter via
`RAIOS_A17_4_HARVEST_ROOT` or the default path above. No rewrite of the
normalizer/differential/mastery/retirement engines is required.

Until then: `A17_4_REAL_DATA_CONSUMPTION=PENDING`.

## 10. No-commit / no-push confirmation (mission safety)

This session did **not**:

- interrupt or inspect a running PowerShell harvest process
- kill Ollama or delete models
- download Qwen3.6
- write to `_raios-a17-native-cortex/experience/raw/teacher-harvest/**`
- write to `_raios-a17-native-cortex/evidence/**`
- write to `_raios-a17-native-cortex/reports/**`
- open or vacuum `_raios-a17-native-cortex/store/a17-cognitive.db`
- modify `RAIOS/V9/**` (see §11)
- rewrite A14/A14.1/A15 receipts
- auto-promote canonical truth
- auto-delete teachers
- invent A17.4 PASS evidence

Cloud delivery of this isolated package uses a feature branch PR into
`codex-clean`. That is packaging of **new** `_raios-a17-integration-wave/`
files only. It is not a commit into the user's live harvest working tree.

## 11. RAIOS/V9 before/after git status

Before and after this wave:

```
git status --short -- RAIOS/V9
(empty)

git diff --stat -- RAIOS/V9
(empty)
```

Identity file `RAIOS/V9/continuity/RAIOS-IDENTITY.json` is unchanged
(read-only bind). Organism identity preserved: `raios.organism.v9`.

## 12. Next recommended action

1. Let the local A17.4 empirical teacher harvest finish without interruption.
2. Copy/read completed harvest artifacts into the adapter (read-only).
3. Run `normalize` then `differential` / `mastery-evaluate` / `retirement-evaluate` on real teacher outputs.
4. Keep `A17_4_REAL_DATA_CONSUMPTION` PENDING until those persisted observations exist.
5. Do not install Qwen3.6 until a verified local artifact and reversible install plan exist.
6. Do not retire any teacher on size, one passing test, or disk pressure.
