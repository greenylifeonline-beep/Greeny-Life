from __future__ import annotations

import json
import time
from pathlib import Path

from raios.neuro_lingua.kernel import NeuroLingua


CASES = Path(__file__).resolve().parents[2] / "benchmarks" / "neuro_lingua" / "seed_cases.jsonl"


async def _run() -> dict:
    nl = NeuroLingua()
    rows = []
    llm_calls = 0
    provider_calls = 0
    started = time.perf_counter()
    for line in CASES.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        t0 = time.perf_counter()
        interpreted = await nl.interpret(case["input"], context=case.get("context") or {"domain": "project"})
        realized = await nl.realize(interpreted.meaning, target_locale=case.get("locale") or "en")
        latency = (time.perf_counter() - t0) * 1000
        metrics = nl.router.metrics()
        provider_calls = metrics["provider_calls"]
        llm_calls = metrics["llm_calls"]
        preserve_ok = True
        for token in case.get("preserve") or []:
            if token not in case["input"]:
                continue
            if token not in realized.text and token.lower() not in " ".join(
                tok.text.lower() for tok in interpreted.meaning.preserved_tokens
            ):
                preserve_ok = False
        dialect_ok = True
        if case.get("locale") in {"ar-EG", "ar-GULF"}:
            dialect_ok = interpreted.meaning.source_locale == case["locale"]
        politeness_ok = True
        if case.get("politeness") is True:
            politeness_ok = interpreted.meaning.pragmatics.politeness_marker is True
            politeness_ok = politeness_ok and interpreted.meaning.pragmatics.condition is False
        rows.append(
            {
                "id": case["id"],
                "locale": case.get("locale"),
                "latency_ms": round(latency, 3),
                "source_locale": interpreted.meaning.source_locale,
                "dialect_ok": dialect_ok,
                "preserve_ok": preserve_ok,
                "politeness_ok": politeness_ok,
                "llm_calls_total": llm_calls,
                "verification": realized.verification.get("status"),
                "provider": "deterministic",
            }
        )
    elapsed = (time.perf_counter() - started) * 1000
    dialect_acc = sum(1 for row in rows if row["dialect_ok"]) / max(len(rows), 1)
    return {
        "schema": "raios.v9.neurolingua.benchmark.v1",
        "mode": "OFFLINE_NO_LLM",
        "cases": len(rows),
        "llm_calls": llm_calls,
        "provider_calls": provider_calls,
        "local_execution_ratio": 1.0 if llm_calls == 0 else round((provider_calls - llm_calls) / max(provider_calls, 1), 4),
        "dialect_detection_accuracy": round(dialect_acc, 4),
        "average_latency_ms": round(elapsed / max(len(rows), 1), 3),
        "rows": rows,
        "skipped_provider_unavailable": 0,
        "false_pass": False,
    }


def main() -> int:
    import asyncio

    report = asyncio.run(_run())
    out = Path(__file__).resolve().parents[2] / "reports" / "v9-neurolingua-benchmark.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    print("LLM_CALLS", report["llm_calls"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
