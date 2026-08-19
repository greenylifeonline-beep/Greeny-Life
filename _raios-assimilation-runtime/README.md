# Live assimilation runtime

Connects the learning observatory to **real** RAIOS interfaces in `_raios-a17-native-cortex` (CCEE). No fake adapters.

```bash
cd /workspace
PYTHONPATH=_raios-a17-native-cortex:_raios-a17-integration-wave/src:_raios-a17-cursor-parallel/src python3 -m _raios-assimilation-runtime contact
PYTHONPATH=... python3 -m _raios-assimilation-runtime discover
PYTHONPATH=... python3 -m _raios-assimilation-runtime cycle
PYTHONPATH=... python3 -m _raios-assimilation-runtime ask --intent "..."
```

State:

- `_raios-assimilation-runtime/state/LIVE-ASSIMILATION-STATE.json`
- `_raios-assimilation-runtime/state/CURRENT-TEACHER-PACKET.json`
- `_raios-learning-observatory/assimilation/queue/ASSIMILATION-QUEUE.json`
