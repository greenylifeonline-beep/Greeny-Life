# RAIOS File Intelligence Fabric (parallel)

Isolated package. It does **not** mutate `RAIOS/V9`, A17 harvest writers, or CCEE `var`.
It prepares RAIOS to operate on both project versions and future repositories without
assuming file type or language.

Policy: **REUSE > ADAPT > WRAP > CREATE**. Magika/Tika/tree-sitter/Ollama are detected,
never blindly installed.

## Commands

```bash
cd /workspace
PYTHONPATH=_raios-file-intelligence-parallel/src python3 -m unittest discover -s _raios-file-intelligence-parallel/tests -v
PYTHONPATH=_raios-file-intelligence-parallel/src python3 -m raios_fi.doctor --report
pwsh -NoProfile -File _raios-file-intelligence-parallel/tests/FILE-INTELLIGENCE-DOCTOR.ps1
```

## Law

- stdout is not evidence
- UNKNOWN stays UNKNOWN
- extension is never sole type authority
- LLM is not the default parser
- original sources are immutable during analysis
- shadow apply only; governed apply is forbidden in this package
- false PASS is impossible (`GATES_SATISFIED` / `FAILED` only)
