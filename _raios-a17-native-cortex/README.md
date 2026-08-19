# RAIOS A18 Continuous Cognitive Evolution Engine

Executable cognitive learning substrate. Not a demo, not a lesson queue,
not an auto-fine-tune loop.

This tree repairs A17.13 certification law (false PASS is impossible) and
implements the CCEE dual-brain runtime. It does **not** mutate `RAIOS/V9`,
delete teachers, fine-tune the main cortex, or pull Qwen3.6.

## Commands

```bash
cd _raios-a17-native-cortex
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 tests/certify_a18_ccee.py
PYTHONPATH=. python3 -m ccee.doctor --report
PYTHONPATH=. python3 -m ccee.boot
pwsh -NoProfile -File tests/CERTIFY-A18-CCEE.ps1
pwsh -NoProfile -File tests/regression/RUN-FALSE-PASS-REGRESSION.ps1
```

## Law

- stdout is not evidence; SHA-256 receipts are evidence
- no model output has execution, canonical, deletion, or promotion authority
- success receipts only after mandatory gates
- child exit != 0 invalidates the parent
- HEALTH_CHECK is not LIVE; chat HTTP 500 cannot mint QWEN_CHAT=PASS
- teacher deletion is forbidden
- forgetting never destroys historical evidence
