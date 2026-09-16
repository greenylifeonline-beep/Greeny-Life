# Wave 00 — files and tests only

C1 authorized this wave as files/tests, not mutation.

Do:

- Keep the gate vector in `WAVE-00.json` and `GATES.json`.
- Keep fail-closed tests in `tests/architecture/test_canonical_convergence_phase0.py`.

Do not:

- Extract `cursor/*`.
- Clean the working tree.
- Rebind C6.
- Mutate `LOCKS.json` / `TASKS.json`.
- Merge, delete, or stop services.

Mutation stays blocked until every `required_before_mutation` predicate is true, including C6 live-bound consumer and an active scoped lease.
