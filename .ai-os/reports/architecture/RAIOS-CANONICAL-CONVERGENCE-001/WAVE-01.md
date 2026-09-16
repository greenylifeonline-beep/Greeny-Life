# Wave 01 — source vs runtime, files and tests only

C1 said «التالي» after D-038. Same mode: files and tests. Not full EXECUTE. Not P1 mutation.

Do:

- Keep the eight-kind contract in `CLASSIFICATION.json`.
- Keep fail-closed tests in `tests/architecture/test_canonical_convergence_phase1.py`.
- Record P0 gate facts in `P0-OBSERVED.json` without rebinding C6.

Do not:

- Move, ignore-only, or delete mixed-kind files.
- Stop services.
- Extract `cursor/*`.
- Rebind C6 or mutate LOCKS/TASKS/SEAT-MAP.

P1 mutation stays blocked until P0 `mutation_allowed` is true.
