# RAIOS A17.14–A23 Cursor Parallel Wave

Isolated implementation of live teacher-student transfer, mastery, retirement,
experience, knowledge, skill compiler, adapter factory, elastic compute, and
autonomic maintenance contracts.

This package does **not** write into live PowerShell A17.4–A17.13 paths,
`RAIOS/V9` canonical state, or production databases.

## Identity

- Organism: RAIOS (`raios.organism.v9`)
- Native Cortex is replaceable, not identity
- Selected cortex target: `qwen3.6:35b-a3b` (not downloaded in this wave)
- Temporary teachers: `granite4:3b`, `qwen2.5-coder:3b`, `deepseek-r1:1.5b`

## Commands

```bash
python3 -m unittest discover -s tests -v
python3 tests/certify_cursor_a17_a23.py
# Windows child process:
pwsh -NoProfile -File tests/CERTIFY-CURSOR-A17-A23.ps1
```

CLI (isolated runtime directory):

```bash
PYTHONPATH=src:_raios-a17-integration-wave/src python3 -m raios_parallel reality-audit --root /tmp/parallel
PYTHONPATH=src:_raios-a17-integration-wave/src python3 -m raios_parallel shared-state --root /tmp/parallel
PYTHONPATH=src:_raios-a17-integration-wave/src python3 -m raios_parallel mastery evaluate cap.x --root /tmp/parallel
PYTHONPATH=src:_raios-a17-integration-wave/src python3 -m raios_parallel retirement status teacher:granite4-3b --root /tmp/parallel
PYTHONPATH=src:_raios-a17-integration-wave/src python3 -m raios_parallel graph --root /tmp/parallel
```

## Safety

- Teacher output is never canonical.
- VALIDATED != CANONICAL.
- MASTERED is impossible without unseen transfer, retention, and independent verification.
- Reading does not pay knowledge debt.
- Skills cannot auto-activate.
- Adapters cannot auto-promote.
- Models are never deleted by this engine.
- Cortex proposals have no execution authority.
- Live A17 writers and `RAIOS/V9` are write-refused.
- Qwen3.6 is not pulled or installed by this wave.

Runtime harvest / Qwen binding is `PENDING_RUNTIME_VALIDATION` in this checkout.
