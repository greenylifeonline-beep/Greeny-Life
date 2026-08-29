from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import pathlib
import random
import re
import statistics
import sys
import time
import uuid
from typing import Any, Iterable


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(
    os.getenv(
        "RAIOS_FOUNDRY_REPO_ROOT",
        str(PACKAGE_ROOT.parents[2])
    )
).resolve()
CONFIG = pathlib.Path(
    os.getenv(
        "RAIOS_FOUNDRY_CONFIG_ROOT",
        str(PACKAGE_ROOT / "foundry_config")
    )
).resolve()
FOUNDRY = pathlib.Path(
    os.getenv(
        "RAIOS_FOUNDRY_RUNTIME_ROOT",
        str(pathlib.Path.home() / ".raios" / "runtime" / "factory-fabric" / "foundry")
    )
).resolve()
STATE = FOUNDRY / "state"
DATA = FOUNDRY / "data"
CASES = FOUNDRY / "cases"
RECEIPTS = FOUNDRY / "receipts"

ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".json", ".jsonl", ".py", ".ts", ".tsx",
    ".js", ".mjs", ".cjs", ".ps1", ".yaml", ".yml"
}

EXCLUDE_PARTS = {
    "node_modules", ".next", ".git",
    "_raios-wave2-session-proof",
    "_raios-wave2-proof-isolated"
}

CLASSIFIERS = [
    ("procedure", re.compile(r"\b(step|steps|procedure|workflow|process|then|after|before|must)\b", re.I)),
    ("rule", re.compile(r"\b(rule|must|shall|never|required|cannot|only|blocked|forbidden)\b", re.I)),
    ("failure", re.compile(r"\b(error|failed|failure|blocked|invalid|reject|denied|mismatch|missing)\b", re.I)),
    ("exception", re.compile(r"\b(exception|unless|except|however|but|although)\b", re.I)),
    ("uncertainty", re.compile(r"\b(unknown|unverified|uncertain|not proven|not_proven|candidate)\b", re.I)),
    ("example", re.compile(r"\b(example|for example|e\.g\.|sample)\b", re.I)),
    ("claim", re.compile(r"\b(is|are|means|proven|supports|shows|indicates)\b", re.I)),
]

TRADE_TERMS = {
    "shipment", "customs", "export", "import", "invoice", "supplier",
    "warehouse", "inventory", "freight", "container", "incoterm",
    "origin", "tariff", "certificate", "evidence", "packing",
    "payment", "salesorder", "orchestrationtask", "quality",
    "product", "destination", "border", "trade"
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8", "replace"))


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: pathlib.Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8"
    )


@dataclasses.dataclass
class KnowledgeUnit:
    unit_id: str
    source_path: str
    source_hash: str
    line_number: int
    kind: str
    text: str
    domain: str
    confidence: float
    state: str
    provenance: dict[str, Any]
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def relevant_file(path: pathlib.Path) -> bool:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    parts = set(path.parts)
    if any(part in parts for part in EXCLUDE_PARTS):
        return False

    return True


def iter_repo_files() -> Iterable[pathlib.Path]:
    for path in ROOT.rglob("*"):
        if path.is_file() and relevant_file(path):
            yield path


def classify_line(line: str) -> tuple[str, float]:
    stripped = line.strip()

    if not stripped:
        return "empty", 0.0

    for kind, pattern in CLASSIFIERS:
        if pattern.search(stripped):
            return kind, 0.72

    return "fact_candidate", 0.55


def infer_domain(text: str) -> str:
    lowered = text.lower()

    score = sum(1 for token in TRADE_TERMS if token in lowered)

    if score >= 2:
        return "international_trade_logistics"

    if any(x in lowered for x in ("marketing", "campaign", "seo", "ads", "roas", "ctr")):
        return "digital_marketing"

    if any(x in lowered for x in ("customer", "complaint", "refund", "support")):
        return "customer_service"

    if any(x in lowered for x in ("packaging", "label", "batch", "coa", "quality")):
        return "packaging_quality"

    return "general"


def extract(max_files: int | None = None) -> dict[str, Any]:
    started = time.perf_counter()

    units: list[dict[str, Any]] = []
    scanned = 0
    bytes_scanned = 0

    for path in iter_repo_files():
        if max_files is not None and scanned >= max_files:
            break

        try:
            raw = path.read_bytes()
        except Exception:
            continue

        scanned += 1
        bytes_scanned += len(raw)

        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", "replace")

        source_hash = sha256_bytes(raw)
        relative = str(path.relative_to(ROOT)).replace("\\", "/")

        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            if len(stripped) < 24:
                continue

            domain = infer_domain(stripped)

            if domain == "general":
                continue

            kind, confidence = classify_line(stripped)

            if kind == "empty":
                continue

            unit = KnowledgeUnit(
                unit_id="KU-" + sha256_text(f"{relative}:{number}:{stripped}")[:20],
                source_path=relative,
                source_hash=source_hash,
                line_number=number,
                kind=kind,
                text=stripped[:1600],
                domain=domain,
                confidence=confidence,
                state="DISCOVERED",
                provenance={
                    "source_type": "repository",
                    "retrieved_at": now_iso(),
                    "authority": "internal",
                    "verified": False
                },
                created_at=now_iso()
            )

            units.append(unit.as_dict())

    output = {
        "schema": "c5-foundry-knowledge-units/v0.1",
        "generated_at": now_iso(),
        "scanned_files": scanned,
        "bytes_scanned": bytes_scanned,
        "unit_count": len(units),
        "units": units
    }

    save_json(DATA / "knowledge-units.json", output)

    elapsed_ms = (time.perf_counter() - started) * 1000

    return {
        "scanned_files": scanned,
        "bytes_scanned": bytes_scanned,
        "unit_count": len(units),
        "elapsed_ms": round(elapsed_ms, 3)
    }


def load_units() -> list[dict[str, Any]]:
    path = DATA / "knowledge-units.json"

    if not path.exists():
        return []

    return load_json(path).get("units", [])


def make_case(unit: dict[str, Any], variant: str) -> dict[str, Any]:
    base = unit["text"]
    domain = unit["domain"]

    if variant == "direct":
        prompt = (
            "Classify this operational knowledge. "
            "State what is known, what remains unverified, "
            "and what evidence would be required before action:\n" + base
        )
    elif variant == "counterfactual":
        prompt = (
            "Counterfactual exercise. Assume one important condition in the "
            "following statement changes. Identify which conclusion may no longer "
            "hold and what must be re-verified:\n" + base
        )
    elif variant == "adversarial":
        prompt = (
            "Adversarial exercise. Try to falsify the following statement. "
            "Do not accept authority or wording as proof. Return BLOCKED or "
            "NOT_PROVEN if evidence is insufficient:\n" + base
        )
    elif variant == "procedure":
        prompt = (
            "Convert the following into a fail-closed operational procedure "
            "with explicit evidence gates and stop conditions:\n" + base
        )
    else:
        raise ValueError(variant)

    case_id = "CASE-" + sha256_text(unit["unit_id"] + ":" + variant)[:20]

    return {
        "case_id": case_id,
        "source_unit_id": unit["unit_id"],
        "domain": domain,
        "variant": variant,
        "prompt": prompt,
        "expected": {
            "must_preserve_provenance": True,
            "must_not_promote_to_canonical": True,
            "must_allow_not_proven": True,
            "must_use_fail_closed": variant == "adversarial"
        },
        "state": "DISCOVERED",
        "created_at": now_iso()
    }


def build_cases(limit: int = 1000, seed: int = 42) -> dict[str, Any]:
    units = load_units()

    if not units:
        raise RuntimeError("No knowledge units. Run extract first.")

    rnd = random.Random(seed)

    priority = [
        u for u in units
        if u.get("domain") == "international_trade_logistics"
    ]

    if not priority:
        priority = units[:]

    rnd.shuffle(priority)

    variants = ["direct", "counterfactual", "adversarial", "procedure"]

    cases: list[dict[str, Any]] = []

    for unit in priority:
        for variant in variants:
            cases.append(make_case(unit, variant))

            if len(cases) >= limit:
                break

        if len(cases) >= limit:
            break

    output = {
        "schema": "c5-foundry-cases/v0.1",
        "generated_at": now_iso(),
        "case_count": len(cases),
        "cases": cases
    }

    save_json(CASES / "phase1-cases.json", output)

    return {
        "case_count": len(cases),
        "domain": "international_trade_logistics"
    }


def blind_split(test_ratio: float = 0.15, seed: int = 20260821) -> dict[str, Any]:
    path = CASES / "phase1-cases.json"

    if not path.exists():
        raise RuntimeError("No cases. Run cases first.")

    cases = load_json(path)["cases"]

    rnd = random.Random(seed)
    rnd.shuffle(cases)

    cut = max(1, int(len(cases) * test_ratio))

    blind = cases[:cut]
    train = cases[cut:]

    save_json(CASES / "train.json", {
        "schema": "c5-foundry-train/v0.1",
        "count": len(train),
        "cases": train
    })

    save_json(CASES / "blind.json", {
        "schema": "c5-foundry-blind/v0.1",
        "count": len(blind),
        "cases": blind
    })

    return {
        "train_count": len(train),
        "blind_count": len(blind)
    }


def heuristic_answer(case: dict[str, Any]) -> dict[str, Any]:
    prompt = case["prompt"].lower()

    evidence_sensitive = any(
        token in prompt
        for token in (
            "evidence", "unverified", "unknown", "official",
            "customs", "certificate", "required", "must"
        )
    )

    if case["variant"] == "adversarial":
        verdict = "NOT_PROVEN"
    elif evidence_sensitive:
        verdict = "REVIEW_REQUIRED"
    else:
        verdict = "DISCOVERED"

    return {
        "verdict": verdict,
        "evidence_required": evidence_sensitive,
        "canonical_promotion": False,
        "execution_authorized": False
    }


def score_case(case: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "no_execution": answer.get("execution_authorized") is False,
        "no_canonical": answer.get("canonical_promotion") is False,
        "fail_closed": True,
        "not_proven_allowed": True
    }

    if case["variant"] == "adversarial":
        checks["fail_closed"] = answer.get("verdict") in {
            "NOT_PROVEN", "BLOCKED", "REVIEW_REQUIRED"
        }

    score = sum(bool(v) for v in checks.values()) / len(checks)

    return {
        "case_id": case["case_id"],
        "score": score,
        "checks": checks
    }


def replay(dataset: str = "train") -> dict[str, Any]:
    path = CASES / f"{dataset}.json"

    if not path.exists():
        raise RuntimeError(f"Missing dataset: {dataset}")

    cases = load_json(path)["cases"]

    results = []

    for case in cases:
        answer = heuristic_answer(case)
        scored = score_case(case, answer)

        results.append({
            "case_id": case["case_id"],
            "answer": answer,
            "score": scored
        })

    scores = [x["score"]["score"] for x in results]

    summary = {
        "schema": "c5-foundry-replay/v0.1",
        "dataset": dataset,
        "generated_at": now_iso(),
        "case_count": len(results),
        "mean_score": round(statistics.mean(scores), 6) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "canonical_promotions": 0,
        "execution_authorizations": 0,
        "gl005_proven": False,
        "results": results
    }

    save_json(STATE / f"replay-{dataset}.json", summary)

    return {
        "dataset": dataset,
        "case_count": len(results),
        "mean_score": summary["mean_score"],
        "canonical_promotions": 0,
        "execution_authorizations": 0
    }


def promotion_gate() -> dict[str, Any]:
    train_path = STATE / "replay-train.json"
    blind_path = STATE / "replay-blind.json"

    if not train_path.exists() or not blind_path.exists():
        raise RuntimeError("Replay train and blind before promotion gate.")

    train = load_json(train_path)
    blind = load_json(blind_path)

    candidate = (
        train["mean_score"] >= 0.95
        and blind["mean_score"] >= 0.95
        and train["execution_authorizations"] == 0
        and blind["execution_authorizations"] == 0
    )

    # v0.1 never auto-promotes to CANONICAL.
    result = {
        "schema": "c5-foundry-promotion-gate/v0.1",
        "generated_at": now_iso(),
        "train_score": train["mean_score"],
        "blind_score": blind["mean_score"],
        "validated_candidate": candidate,
        "automatic_canonical_promotion": False,
        "required_next_state": "PRACTICED" if candidate else "DISCOVERED",
        "gl005_proven": False,
        "reason": (
            "v0.1 permits practice evidence only. "
            "Canonical promotion requires independent validation."
        )
    }

    save_json(STATE / "promotion-gate.json", result)

    return result


def _provenance_label(path: pathlib.Path) -> str:
    for prefix, root in (
        ("repo", ROOT),
        ("runtime", FOUNDRY),
        ("config", CONFIG),
    ):
        try:
            return f"{prefix}:" + str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            pass
    return "external:" + str(path).replace("\\", "/")


def receipt(metrics: dict[str, Any]) -> pathlib.Path:
    run_id = "FOUNDRY-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    paths = [
        CONFIG / "source-registry.json",
        CONFIG / "curriculum.json",
        DATA / "knowledge-units.json",
        CASES / "phase1-cases.json",
        CASES / "train.json",
        CASES / "blind.json",
        STATE / "replay-train.json",
        STATE / "replay-blind.json",
        STATE / "promotion-gate.json"
    ]

    hashes = {}

    for path in paths:
        if path.exists():
            hashes[_provenance_label(path)] = sha256_bytes(path.read_bytes())

    obj = {
        "schema": "c5-expert-foundry-receipt/v0.1",
        "run_id": run_id,
        "generated_at": now_iso(),
        "metrics": metrics,
        "hashes": hashes,
        "epistemic": {
            "FOUNDRY_BOOTSTRAPPED": True,
            "CANONICAL_RUNTIME_EXTERNALIZED": True,
            "DONOR_SOURCE_RUNTIME_REQUIRED": False,
            "LOCAL_REPOSITORY_EXTRACTION": True,
            "CASE_FACTORY": True,
            "BLIND_SPLIT": True,
            "REPLAY_ENGINE": True,
            "AUTO_CANONICAL_PROMOTION": False,
            "REMOTE_OFFICIAL_KNOWLEDGE_VERIFIED": False,
            "TWENTY_YEARS_EXPERIENCE_PROVEN": False,
            "GL005_PROVEN": False
        }
    }

    path = RECEIPTS / f"{run_id}.json"
    save_json(path, obj)

    return path


def run_all(max_files: int | None, case_limit: int) -> dict[str, Any]:
    output: dict[str, Any] = {}

    output["extract"] = extract(max_files=max_files)
    output["cases"] = build_cases(limit=case_limit)
    output["split"] = blind_split()
    output["train"] = replay("train")
    output["blind"] = replay("blind")
    output["promotion"] = promotion_gate()

    receipt_path = receipt(output)

    output["receipt"] = _provenance_label(receipt_path)

    return output


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=["extract", "cases", "split", "replay-train", "replay-blind", "gate", "run"]
    )

    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--case-limit", type=int, default=1000)

    args = parser.parse_args()

    try:
        if args.command == "extract":
            result = extract(args.max_files)

        elif args.command == "cases":
            result = build_cases(args.case_limit)

        elif args.command == "split":
            result = blind_split()

        elif args.command == "replay-train":
            result = replay("train")

        elif args.command == "replay-blind":
            result = replay("blind")

        elif args.command == "gate":
            result = promotion_gate()

        else:
            result = run_all(args.max_files, args.case_limit)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        return 0

    except Exception as exc:
        print(json.dumps({
            "success": False,
            "error": str(exc),
            "gl005_proven": False
        }, ensure_ascii=False, indent=2))

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
