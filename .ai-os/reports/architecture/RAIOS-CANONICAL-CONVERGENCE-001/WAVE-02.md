# Wave 02 — HEAD truth, files and tests only

C1 said «التالي» after D-039. Same mode: files and tests. Not full EXECUTE. Not C5 cutover.

Do:

- Keep named stamps in `HEAD-SNAPSHOT.json`.
- Keep the model in `HEAD-TRUTH-MODEL.json`.
- Keep fail-closed tests in `tests/architecture/test_canonical_convergence_phase2.py`.

Do not:

- Rewrite `EXECUTIVE-PROGRAM.json` `head` as current.
- Cut over C5.
- Relocate runtime state.
- Rebind C6 or mutate LOCKS/TASKS/SEAT-MAP.

`2efd081` and `96a1e7e` stay historical/conflicting until a live runtime proves it still uses them.
