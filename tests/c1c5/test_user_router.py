from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / ".ai-os" / "control" / "RAIOS-USER-ROUTER-V1.py"


def _load():
    spec = importlib.util.spec_from_file_location("raios_user_router", ROUTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_user_router_file_is_present():
    assert ROUTER.is_file()


def test_route_one_c5_public_is_proven_e2e(monkeypatch):
    mod = _load()

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"status": "OK", "response": "Hello C1", "content": "Hello C1"}).encode()

    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = mod.route_one("C1@AG", "C5-PUBLIC", "hi", correlation="COR-TEST-E2E")
    assert out["status"] == "PROVEN_E2E"
    assert out["correlation_id"] == "COR-TEST-E2E"
    assert out["wal_written"] is False
    assert out["receipt"]["sha256"]
    assert out["response"]["response"] == "Hello C1"
