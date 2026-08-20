from __future__ import annotations

import json
from pathlib import Path

import pytest

from raios.config import load_neuro_lingua_config
from raios.neuro_lingua import NeuroLingua
from raios.providers import LocalDeterministicProvider, ProviderRegistry
from raios.wal import CognitiveWAL


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def nl(tmp_path: Path, repo_root: Path) -> NeuroLingua:
    config = load_neuro_lingua_config(repo_root)
    config.wal_path = tmp_path / "cognitive_wal.jsonl"
    config.evolution_inbox_path = tmp_path / "evolution_inbox.jsonl"
    config.offline = True
    config.allow_llm_adjudication = False
    config.allow_back_translation = False
    return NeuroLingua(
        config,
        providers=ProviderRegistry([LocalDeterministicProvider()]),
        wal=CognitiveWAL(config.wal_path),
    )


def pytest_sessionfinish(session, exitstatus):
    report_path = Path(__file__).resolve().parents[2] / "reports" / "v9-neurolingua-test-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    collected = getattr(session, "items", [])
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    passed = failed_n = skipped = 0
    details: list[dict] = []
    if reporter:
        passed = len(reporter.stats.get("passed", []))
        failed_n = len(reporter.stats.get("failed", []))
        skipped = len(reporter.stats.get("skipped", []))
        for outcome, key in (("passed", "passed"), ("failed", "failed"), ("skipped", "skipped")):
            for item in reporter.stats.get(key, []):
                nodeid = getattr(item, "nodeid", str(item))
                longrepr = str(getattr(item, "longrepr", "") or "")
                details.append(
                    {
                        "nodeid": nodeid,
                        "outcome": outcome,
                        "longrepr": longrepr[:2000] if outcome == "failed" else "",
                    }
                )
    payload = {
        "suite": "RAIOS V9.NL-0 NeuroLingua",
        "exitstatus": int(exitstatus),
        "collected": len(collected),
        "passed": passed,
        "failed": failed_n,
        "skipped": skipped,
        "gpu_required": False,
        "llm_required": False,
        "offline": True,
        "tests": details,
        "hidden_failures": False,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
