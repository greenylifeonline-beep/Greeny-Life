#!/usr/bin/env python3
"""Offline NeuroLingua NL-0 benchmark runner.

Runs even when no LLM provider is available. Provider-dependent expectations
are skipped rather than faked.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.config import load_neuro_lingua_config  # noqa: E402
from raios.neuro_lingua.kernel import NeuroLingua  # noqa: E402
from raios.providers import LocalDeterministicProvider, ProviderRegistry  # noqa: E402
from raios.wal import CognitiveWAL  # noqa: E402


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _contains_all(haystack: str, needles: list[str]) -> tuple[bool, list[str]]:
    missing = [item for item in needles if item not in haystack]
    return not missing, missing


async def run_case(kernel: NeuroLingua, case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    result = await kernel.interpret(text=case["text"], context=case.get("context") or {})
    meaning = result.meaning
    expect = case.get("expect") or {}
    failures: list[str] = []
    skips: list[str] = []

    if "locale" in expect and meaning.detection.locale != expect["locale"]:
        failures.append(f"locale {meaning.detection.locale!r} != {expect['locale']!r}")
    if "language" in expect and meaning.detection.language != expect["language"]:
        failures.append(f"language {meaning.detection.language!r} != {expect['language']!r}")
    if "dialect" in expect and meaning.detection.dialect != expect["dialect"]:
        failures.append(f"dialect {meaning.detection.dialect!r} != {expect['dialect']!r}")
    if expect.get("code_switched") and not meaning.detection.code_switched:
        failures.append("expected code_switched")
    if "action" in expect and meaning.pragmatics.action != expect["action"]:
        failures.append(f"action {meaning.pragmatics.action!r} != {expect['action']!r}")
    if "deadline" in expect and meaning.pragmatics.deadline != expect["deadline"]:
        failures.append(f"deadline {meaning.pragmatics.deadline!r}")
    if expect.get("politeness_marker") and not meaning.pragmatics.politeness_marker:
        failures.append("missing politeness_marker")
    if expect.get("not_logical_condition") and not meaning.pragmatics.not_logical_condition:
        failures.append("politeness treated without not_logical_condition evidence")
    if "concepts" in expect:
        got = {c.concept_id for c in meaning.concepts}
        missing = [c for c in expect["concepts"] if c not in got]
        if missing:
            failures.append(f"missing concepts {missing}")
    if "intent" in expect and meaning.intent != expect["intent"]:
        failures.append(f"intent {meaning.intent!r} != {expect['intent']!r}")
    if "numbers" in expect:
        surfaces = {s.surface for s in meaning.numbers}
        missing = [n for n in expect["numbers"] if n not in surfaces]
        if missing:
            failures.append(f"missing numbers {missing}")
    if "preserve" in expect:
        blob = meaning.source_text + " " + " ".join(meaning.preserved_surfaces())
        blob += " " + " ".join(s.text for s in meaning.segments)
        missing = [tok for tok in expect["preserve"] if tok not in blob]
        if missing:
            failures.append(f"missing preserved {missing}")

    realized = None
    if "realize" in case:
        spec = case["realize"]
        rendered = await kernel.realize(meaning, spec["target_locale"])
        realized = rendered.to_dict()
        ok, missing = _contains_all(rendered.text, spec.get("must_include") or [])
        if not ok:
            failures.append(f"realize missing {missing}")
        forbidden = spec.get("must_not_include") or []
        leaked = [tok for tok in forbidden if tok in rendered.text]
        if leaked:
            failures.append(f"realize leaked {leaked}")

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "id": case["id"],
        "passed": not failures,
        "failures": failures,
        "skips": skips,
        "latency_ms": latency_ms,
        "llm_calls": result.metrics.llm_calls,
        "provider_calls": result.metrics.provider_calls,
        "local_execution_ratio": result.metrics.local_execution_ratio,
        "locale": meaning.detection.locale,
        "language": meaning.detection.language,
        "dialect": meaning.detection.dialect,
        "code_switched": meaning.detection.code_switched,
        "language_detection_ok": (
            expect.get("locale") in (None, meaning.detection.locale)
            and expect.get("language") in (None, meaning.detection.language)
        ),
        "dialect_detection_ok": expect.get("dialect", meaning.detection.dialect) == meaning.detection.dialect,
        "intent": meaning.intent,
        "numbers": [s.surface for s in meaning.numbers],
        "identifiers": [s.surface for s in meaning.identifiers],
        "realized": realized,
        "verification": realized.get("verification") if realized else None,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows) or 1
    def ratio(key: str) -> float:
        return round(sum(1 for row in rows if row.get(key)) / n, 4)

    return {
        "cases": len(rows),
        "passed": sum(1 for row in rows if row["passed"]),
        "failed": sum(1 for row in rows if not row["passed"]),
        "language_detection_accuracy": ratio("language_detection_ok"),
        "dialect_detection_accuracy": ratio("dialect_detection_ok"),
        "mean_latency_ms": round(sum(row["latency_ms"] for row in rows) / n, 3),
        "total_llm_calls": sum(row["llm_calls"] for row in rows),
        "total_provider_calls": sum(row["provider_calls"] for row in rows),
        "mean_local_execution_ratio": round(
            sum(row["local_execution_ratio"] for row in rows) / n, 4
        ),
        "llm_required": False,
        "offline": True,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "benchmarks/neuro_lingua/seed_cases.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/v9-neurolingua-benchmark.json",
    )
    args = parser.parse_args()
    config = load_neuro_lingua_config(args.repo_root)
    wal_dir = args.repo_root / "intelligence/knowledge_base/neuro_lingua"
    wal_dir.mkdir(parents=True, exist_ok=True)
    config.wal_path = wal_dir / "benchmark_wal.jsonl"
    config.evolution_inbox_path = wal_dir / "benchmark_evolution.jsonl"
    kernel = NeuroLingua(
        config,
        providers=ProviderRegistry([LocalDeterministicProvider()]),
        wal=CognitiveWAL(config.wal_path),
    )
    cases = load_cases(args.cases)
    rows = [await run_case(kernel, case) for case in cases]
    report = {
        "suite": "RAIOS V9.NL-0 NeuroLingua",
        "generated": True,
        "summary": summarize(rows),
        "cases": rows,
        "notes": [
            "Benchmark ran fully offline with the local deterministic provider.",
            "No LLM calls were made. Provider-dependent checks are not faked.",
            "Back-translation is disabled by default and was not executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
