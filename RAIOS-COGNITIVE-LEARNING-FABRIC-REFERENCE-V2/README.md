# RAIOS Cognitive Learning Fabric — Reference V2

Standalone, executable reference package. It is not a RAIOS runtime integration.

## Test command

```bash
python3 run_tests.py
```

## Contract

The fabric stores references into an external Shared Cognitive Exchange:

- `task://`
- `result://`
- `artifact://sha256/...`
- `evidence://`
- `failure://`
- `experience://`
- `skill://`

It does not host tasks, artifacts, or evidence bodies.

Observable decision records use `decision_summary`, `evidence_basis`, `actions_taken`, `correction_summary`, and `uncertainty`. Private chain-of-thought is not a stored field.
