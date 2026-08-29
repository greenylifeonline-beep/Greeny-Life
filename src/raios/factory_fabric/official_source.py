from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Any

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.getenv("RAIOS_FOUNDRY_REPO_ROOT", str(PACKAGE_ROOT.parents[2]))).resolve()
FOUNDRY = pathlib.Path(os.getenv("RAIOS_FOUNDRY_RUNTIME_ROOT", str(pathlib.Path.home() / ".raios" / "runtime" / "factory-fabric" / "foundry"))).resolve()

CONFIG = PACKAGE_ROOT / "foundry_config"
DATA = FOUNDRY / "data"
RECEIPTS = FOUNDRY / "receipts"

USER_AGENT = "RAIOS-C5-Expert-Foundry/0.2 (+read-only-official-source-harvester)"

DEFAULT_SOURCES = [
    {
        "source_id": "EG-GOEIC-REGULATIONS",
        "jurisdiction": "EGYPT",
        "authority": "official",
        "url": "https://www.goeic.gov.eg/en/laws-and-decisions/list/967",
        "domain": "international_trade"
    },
    {
        "source_id": "EG-GOEIC-DECISIONS",
        "jurisdiction": "EGYPT",
        "authority": "official",
        "url": "https://www.goeic.gov.eg/en/laws-and-decisions/list",
        "domain": "international_trade"
    },
    {
        "source_id": "EG-NAFEZA-ACI",
        "jurisdiction": "EGYPT",
        "authority": "official",
        "url": "https://www.nafeza.gov.eg/en/pages/15",
        "domain": "customs_aci"
    },
    {
        "source_id": "EG-NAFEZA-ACI-DOCS",
        "jurisdiction": "EGYPT",
        "authority": "official",
        "url": "https://www.nafeza.gov.eg/en/pages/32",
        "domain": "customs_documents"
    },
    {
        "source_id": "GCC-SECRETARIAT",
        "jurisdiction": "GCC",
        "authority": "official",
        "url": "https://www.gcc-sg.org/",
        "domain": "international_trade"
    },
    {
        "source_id": "EU-ACCESS2MARKETS",
        "jurisdiction": "EU",
        "authority": "official",
        "url": "https://trade.ec.europa.eu/access-to-markets/",
        "domain": "international_trade"
    }
]

KEY_TERMS = (
    "import", "export", "customs", "shipment", "cargo", "invoice",
    "packing", "origin", "certificate", "tariff", "inspection",
    "aci", "air", "sea", "freight", "prohibited", "required",
    "registration", "clearance", "goods", "regulation", "decision",
    "منشور", "تصدير", "استيراد", "جمرك", "شحنة", "شحن",
    "فاتورة", "منشأ", "شهادة", "قرار", "قانون"
)


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def clean_lines(html: str) -> list[str]:
    parser = TextExtractor()
    parser.feed(html)

    joined = "\n".join(parser.parts)

    output: list[str] = []

    for raw in joined.splitlines():
        line = " ".join(raw.split()).strip()

        if len(line) < 20:
            continue

        low = line.lower()

        if any(term in low for term in KEY_TERMS):
            output.append(line[:3000])

    seen = set()
    unique = []

    for line in output:
        key = hashlib.sha256(line.encode("utf-8")).hexdigest()

        if key not in seen:
            seen.add(key)
            unique.append(line)

    return unique


def fetch(source: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    retrieved_at = iso_now()

    req = urllib.request.Request(
        source["url"],
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml"
        }
    )

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200)
            content_type = resp.headers.get("Content-Type", "")
            final_url = resp.geturl()

        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

        text = body.decode("utf-8", "replace")
        lines = clean_lines(text)

        return {
            "source_id": source["source_id"],
            "jurisdiction": source["jurisdiction"],
            "authority": source["authority"],
            "domain": source["domain"],
            "requested_url": source["url"],
            "final_url": final_url,
            "http_status": status,
            "content_type": content_type,
            "retrieved_at": retrieved_at,
            "elapsed_ms": elapsed_ms,
            "raw_sha256": sha256(body),
            "semantic_line_count": len(lines),
            "semantic_lines": lines,
            "state": "DISCOVERED",
            "verified_current": False,
            "claim_authorization": False,
            "execution_authority": False
        }

    except Exception as exc:
        return {
            "source_id": source["source_id"],
            "jurisdiction": source["jurisdiction"],
            "authority": source["authority"],
            "domain": source["domain"],
            "requested_url": source["url"],
            "retrieved_at": retrieved_at,
            "fetch_error": str(exc),
            "state": "DISCOVERED",
            "verified_current": False,
            "claim_authorization": False,
            "execution_authority": False
        }


def make_units(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units = []

    for record in records:
        for index, line in enumerate(record.get("semantic_lines", []), start=1):
            unit_hash = hashlib.sha256(
                f'{record["source_id"]}:{record.get("raw_sha256")}:{index}:{line}'.encode("utf-8")
            ).hexdigest()

            units.append({
                "unit_id": "OFF-KU-" + unit_hash[:24],
                "source_id": record["source_id"],
                "jurisdiction": record["jurisdiction"],
                "authority": record["authority"],
                "domain": record["domain"],
                "source_url": record.get("final_url", record["requested_url"]),
                "source_raw_sha256": record.get("raw_sha256"),
                "retrieved_at": record["retrieved_at"],
                "last_verified_at": None,
                "effective_from": None,
                "effective_until": None,
                "supersedes": [],
                "text": line,
                "state": "DISCOVERED",
                "verification_status": "UNVERIFIED_CURRENTNESS",
                "stale": "UNKNOWN",
                "execution_authority": False
            })

    return units


def build_cases(units: list[dict[str, Any]], limit: int = 2000) -> list[dict[str, Any]]:
    cases = []

    for unit in units:
        base = {
            "source_unit_id": unit["unit_id"],
            "source_id": unit["source_id"],
            "jurisdiction": unit["jurisdiction"],
            "source_url": unit["source_url"],
            "state": "DISCOVERED",
            "execution_authority": False
        }

        templates = [
            (
                "verification",
                "Determine what this official-source excerpt appears to claim, "
                "but do not treat retrieval as proof of current legal applicability. "
                "List what must be verified before operational use:\n"
            ),
            (
                "corridor",
                "Apply this excerpt hypothetically to a trade corridor. "
                "State jurisdiction, scope uncertainty, missing product/HS/destination facts, "
                "and stop if applicability is not established:\n"
            ),
            (
                "adversarial",
                "Try to falsify operational use of this excerpt. Check age, scope, "
                "supersession, jurisdiction and missing context. Prefer NOT_PROVEN over invention:\n"
            ),
            (
                "procedure",
                "Transform this excerpt into a draft evidence-gated procedure. "
                "Every irreversible action must remain unauthorized until validated:\n"
            )
        ]

        for variant, prefix in templates:
            case_hash = hashlib.sha256(
                f'{unit["unit_id"]}:{variant}'.encode()
            ).hexdigest()

            cases.append({
                **base,
                "case_id": "OFF-CASE-" + case_hash[:24],
                "variant": variant,
                "prompt": prefix + unit["text"],
                "required_behaviour": {
                    "preserve_provenance": True,
                    "allow_not_proven": True,
                    "check_currentness": True,
                    "check_scope": True,
                    "no_execution": True,
                    "no_canonical_auto_promotion": True
                }
            })

            if len(cases) >= limit:
                return cases

    return cases


def save_json(path: pathlib.Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()

    records = [fetch(source) for source in DEFAULT_SOURCES]

    success_records = [
        r for r in records
        if r.get("http_status") == 200
    ]

    units = make_units(success_records)
    cases = build_cases(units, args.limit)

    snapshot = {
        "schema": "c5-foundry-official-snapshot/v0.2",
        "generated_at": iso_now(),
        "source_count": len(records),
        "successful_source_count": len(success_records),
        "records": records,
        "epistemic": {
            "retrieval_proven": len(success_records) > 0,
            "legal_currentness_proven": False,
            "operational_applicability_proven": False,
            "automatic_canonical_promotion": False,
            "gl005_proven": False
        }
    }

    units_obj = {
        "schema": "c5-foundry-official-units/v0.2",
        "generated_at": iso_now(),
        "unit_count": len(units),
        "units": units
    }

    cases_obj = {
        "schema": "c5-foundry-official-cases/v0.2",
        "generated_at": iso_now(),
        "case_count": len(cases),
        "cases": cases
    }

    snapshot_path = DATA / "official-source-snapshot.json"
    units_path = DATA / "official-knowledge-units.json"
    cases_path = FOUNDRY / "cases" / "official-cases.json"

    save_json(snapshot_path, snapshot)
    save_json(units_path, units_obj)
    save_json(cases_path, cases_obj)

    receipt_payload = {
        "schema": "c5-foundry-official-harvest-receipt/v0.2",
        "generated_at": iso_now(),
        "sources_attempted": len(records),
        "sources_retrieved_200": len(success_records),
        "knowledge_units": len(units),
        "training_cases": len(cases),
        "hashes": {
            str(snapshot_path.relative_to(ROOT)).replace("\\", "/"): sha256(snapshot_path.read_bytes()),
            str(units_path.relative_to(ROOT)).replace("\\", "/"): sha256(units_path.read_bytes()),
            str(cases_path.relative_to(ROOT)).replace("\\", "/"): sha256(cases_path.read_bytes())
        },
        "epistemic": {
            "REMOTE_OFFICIAL_RETRIEVAL": len(success_records) > 0,
            "REMOTE_OFFICIAL_ASSIMILATION": len(units) > 0,
            "LEGAL_CURRENTNESS_PROVEN": False,
            "REAL_EXPERT_EQUIVALENCE": False,
            "AUTO_CANONICAL_PROMOTION": False,
            "GL005_PROVEN": False
        }
    }

    receipt_name = "FOUNDRY-OFFICIAL-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
    receipt_path = RECEIPTS / receipt_name

    save_json(receipt_path, receipt_payload)

    print(json.dumps({
        "success": True,
        "sources_attempted": len(records),
        "sources_retrieved_200": len(success_records),
        "knowledge_units": len(units),
        "cases": len(cases),
        "receipt": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
        "legal_currentness_proven": False,
        "real_expert_equivalence": False,
        "gl005_proven": False
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
