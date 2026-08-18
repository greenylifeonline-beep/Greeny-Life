# RAIOS A17 Integration Wave (X1–X3)

Isolated implementation of A17.5–A17.10 contracts/core, plus A18/A19
foundations. This package does **not** write into live A17.4 harvest paths,
RAIOS/V9 canonical state, or production databases.

## Identity

- Organism: RAIOS (`raios.organism.v9`)
- Native Cortex family: Qwen (replaceable provider, not identity)
- Selected master candidate: Qwen3.6-35B-A3B (not downloaded in this wave)
- Temporary teachers: `granite4:3b`, `qwen2.5-coder:3b`, `deepseek-r1:1.5b`

## Commands

```bash
python3 -m unittest discover -s tests -v
python3 tests/certify_a17_x1_x3.py
# Windows child process:
pwsh -NoProfile -File tests/CERTIFY-A17-X1-X3.ps1
```

CLI (isolated runtime directory):

```bash
PYTHONPATH=src python3 -m raios_wave identity --root /tmp/wave
PYTHONPATH=src python3 -m raios_wave mastery-evaluate cap.x --root /tmp/wave
PYTHONPATH=src python3 -m raios_wave competency-status cap.x --root /tmp/wave
PYTHONPATH=src python3 -m raios_wave teacher-dependency cap.x --root /tmp/wave
PYTHONPATH=src python3 -m raios_wave capability-gap cap.x --root /tmp/wave
PYTHONPATH=src python3 -m raios_wave a17-4-status --root /tmp/wave
```

## Safety

- Teacher output is never canonical.
- VALIDATED != CANONICAL.
- Learning debt cannot auto-pay.
- Models are never deleted by this engine.
- Cortex proposals have no execution authority.
- A17.4 live writers are read-only / refused.
