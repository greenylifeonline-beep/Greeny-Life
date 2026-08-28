from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parents[3]
FOUNDRY = ROOT / "RAIOS" / "V9" / "foundry"

DATA = FOUNDRY / "data"
STATE = FOUNDRY / "state"
CASES = FOUNDRY / "cases"
RECEIPTS = FOUNDRY / "receipts"


DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b"),
    re.compile(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})\b"),
]

YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")

NUMBER_PATTERNS = [
    re.compile(
        r"\b(?:decision|decree|regulation|circular|notice|law|resolution)"
        r"\s*(?:no\.?|number)?\s*[:#-]?\s*([0-9]{1,6})"
        r"(?:\s*(?:of|/)\s*(20\d{2}))?",
        re.I,
    ),
    re.compile(
        r"(?:قرار|منشور|قانون|لائحة|تعليمات)"
        r"\s*(?:رقم)?\s*([0-9]{1,6})"
        r"(?:\s*(?:لسنة|لعام|/)\s*(20\d{2}))?",
        re.I,
    ),
]

SUPERSESSION_TERMS = {
    "explicit_replace": [
        "replaces",
        "replaced by",
        "supersedes",
        "superseded by",
        "shall replace",
        "in place of",
        "يلغي",
        "يحل محل",
        "يستبدل",
        "إلغاء",
    ],
    "amendment": [
        "amends",
        "amended",
        "amendment",
        "modifies",
        "modified",
        "تعديل",
        "يعدل",
        "المعدل",
    ],
    "effective": [
        "effective from",
        "enters into force",
        "comes into force",
        "applicable from",
        "يسري اعتبارا",
        "يعمل به اعتبارا",
        "نافذ من",
    ],
    "expiry": [
        "expires",
        "valid until",
        "effective until",
        "ceases to apply",
        "ينتهي",
        "ساري حتى",
    ],
}

SCOPE_TERMS = {
    "food": [
        "food", "honey", "spice", "oil", "agricultural",
        "غذاء", "غذائي", "عسل", "توابل", "زيت", "زراعي"
    ],
    "air_cargo": [
        "air cargo", "air freight", "aviation", "airport",
        "شحن جوي", "جوي", "طيران"
    ],
    "sea_cargo": [
        "sea cargo", "sea freight", "maritime", "port", "container",
        "شحن بحري", "بحري", "ميناء", "حاوية"
    ],
    "customs": [
        "customs", "clearance", "declaration", "aci", "acid",
        "جمارك", "جمركي", "إفراج", "نافذة"
    ],
    "origin": [
        "origin", "certificate of origin", "rules of origin",
        "منشأ", "شهادة المنشأ"
    ],
    "invoice": [
        "invoice", "commercial invoice",
        "فاتورة", "الفاتورة التجارية"
    ],
    "packing": [
        "packing list", "packaging", "packing",
        "قائمة التعبئة", "تعبئة", "تغليف"
    ],
    "inspection": [
        "inspection", "conformity", "quality",
        "فحص", "مطابقة", "جودة"
    ],
}

CORRIDOR_JURISDICTIONS = {
    "EGYPT_GCC": {"EGYPT", "GCC"},
    "GCC_EGYPT": {"GCC", "EGYPT"},
    "EGYPT_EU": {"EGYPT", "EU"},
    "EU_EGYPT": {"EU", "EGYPT"},
    "GCC_EU": {"GCC", "EU"},
    "EU_GCC": {"EU", "GCC"},
    "INTRA_GCC": {"GCC"},
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
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
            sort_keys=True
        ),
        encoding="utf-8"
    )


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def extract_years(text: str) -> list[int]:
    years = {
        int(x)
        for x in YEAR_PATTERN.findall(text)
        if 2000 <= int(x) <= 2100
    }

    return sorted(years)


def extract_dates(text: str) -> list[str]:
    found = set()

    for pattern_index, pattern in enumerate(DATE_PATTERNS):
        for match in pattern.findall(text):
            try:
                if pattern_index == 0:
                    year, month, day = map(int, match)
                else:
                    day, month, year = map(int, match)

                value = dt.date(year, month, day).isoformat()
                found.add(value)

            except Exception:
                continue

    return sorted(found)


def extract_document_numbers(text: str) -> list[dict[str, Any]]:
    output = []

    for pattern in NUMBER_PATTERNS:
        for match in pattern.findall(text):
            number = match[0] if isinstance(match, tuple) else match

            year = None

            if isinstance(match, tuple) and len(match) > 1 and match[1]:
                year = int(match[1])

            output.append({
                "number": str(number),
                "year": year
            })

    unique = []
    seen = set()

    for item in output:
        key = (item["number"], item["year"])

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def detect_supersession_language(text: str) -> list[dict[str, Any]]:
    lowered = normalize_text(text)

    findings = []

    for relation, terms in SUPERSESSION_TERMS.items():
        for term in terms:
            if term in lowered:
                findings.append({
                    "relation_candidate": relation,
                    "matched_term": term
                })

    return findings


def detect_scope(text: str) -> list[str]:
    lowered = normalize_text(text)

    output = []

    for scope, terms in SCOPE_TERMS.items():
        if any(term in lowered for term in terms):
            output.append(scope)

    return sorted(set(output))


def infer_currentness(
    unit: dict[str, Any],
    retrieved_at: str,
    source_record: dict[str, Any] | None,
) -> dict[str, Any]:

    text = unit.get("text", "")

    years = extract_years(text)
    dates = extract_dates(text)
    relationships = detect_supersession_language(text)

    retrieved_year = dt.datetime.fromisoformat(
        retrieved_at.replace("Z", "+00:00")
    ).year

    newest_year = max(years) if years else None

    age_years = (
        retrieved_year - newest_year
        if newest_year is not None
        else None
    )

    # IMPORTANT:
    # This is only a triage classifier.
    # It MUST NOT claim legal currentness.

    if source_record and source_record.get("http_status") != 200:
        triage = "SOURCE_FETCH_UNRELIABLE"

    elif newest_year is None:
        triage = "CURRENTNESS_UNKNOWN"

    elif age_years < 0:
        triage = "FUTURE_OR_DATE_PARSE_REVIEW"

    elif age_years == 0:
        triage = "RECENT_DATE_CANDIDATE"

    elif age_years <= 1:
        triage = "RECENT_DATE_CANDIDATE"

    elif age_years <= 3:
        triage = "CURRENTNESS_REVIEW_REQUIRED"

    else:
        triage = "STALE_RISK"

    if relationships:
        triage = "SUPERSESSION_REVIEW_REQUIRED"

    return {
        "years_found": years,
        "dates_found": dates,
        "newest_year": newest_year,
        "age_years_at_retrieval": age_years,
        "supersession_language": relationships,
        "triage": triage,
        "legal_currentness_proven": False,
        "operational_applicability_proven": False,
    }


def candidate_identity(unit: dict[str, Any]) -> dict[str, Any]:
    text = unit.get("text", "")

    return {
        "document_number_candidates": extract_document_numbers(text),
        "scope_candidates": detect_scope(text),
        "jurisdiction": unit.get("jurisdiction"),
        "source_id": unit.get("source_id"),
    }


def build_enriched_units(
    units: list[dict[str, Any]],
    snapshot: dict[str, Any]
) -> list[dict[str, Any]]:

    by_source = {
        record.get("source_id"): record
        for record in snapshot.get("records", [])
    }

    enriched = []

    for unit in units:
        source_record = by_source.get(unit.get("source_id"))

        currentness = infer_currentness(
            unit,
            unit.get("retrieved_at") or snapshot.get("generated_at"),
            source_record
        )

        identity = candidate_identity(unit)

        enriched.append({
            **unit,
            "document_identity_candidates": identity,
            "currentness_analysis": currentness,
            "scope_candidates": identity["scope_candidates"],

            # v0.3 still fail-closed.
            "state": "DISCOVERED",
            "verification_status": "UNVERIFIED_CURRENTNESS",
            "legal_currentness_proven": False,
            "operational_applicability_proven": False,
            "execution_authority": False,
            "canonical_promotion_allowed": False,
        })

    return enriched


def build_candidate_groups(
    units: list[dict[str, Any]]
) -> list[dict[str, Any]]:

    groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    for unit in units:
        identity = unit["document_identity_candidates"]

        doc_candidates = identity.get("document_number_candidates", [])

        if doc_candidates:
            for candidate in doc_candidates:
                number = candidate.get("number")
                year = candidate.get("year")

                key = (
                    f'{unit.get("jurisdiction")}:'
                    f'{unit.get("source_id")}:'
                    f'{number}:'
                    f'{year}'
                )

                groups[key].append(unit)

        else:
            # Weak semantic grouping for review only.
            scopes = ",".join(unit.get("scope_candidates", []))

            key = (
                f'{unit.get("jurisdiction")}:'
                f'{unit.get("source_id")}:'
                f'SCOPE:{scopes}'
            )

            groups[key].append(unit)

    output = []

    for key, members in groups.items():
        if len(members) < 2:
            continue

        years = sorted({
            year
            for member in members
            for year in member["currentness_analysis"]["years_found"]
        })

        supersession_candidates = [
            member["unit_id"]
            for member in members
            if member["currentness_analysis"]["supersession_language"]
        ]

        output.append({
            "group_id": "CG-" + sha256_text(key)[:24],
            "group_key": key,
            "member_count": len(members),
            "unit_ids": [m["unit_id"] for m in members],
            "years": years,
            "supersession_candidate_unit_ids": supersession_candidates,
            "relationship_status": (
                "SUPERSESSION_REVIEW_REQUIRED"
                if supersession_candidates
                else "VERSION_RELATIONSHIP_UNKNOWN"
            ),
            "automatic_supersession_decision": False
        })

    return output


def corridor_scope_matrix(
    units: list[dict[str, Any]]
) -> dict[str, Any]:

    matrix = {}

    for corridor, jurisdictions in CORRIDOR_JURISDICTIONS.items():
        relevant = [
            unit
            for unit in units
            if unit.get("jurisdiction") in jurisdictions
        ]

        scope_counts = collections.Counter()

        for unit in relevant:
            for scope in unit.get("scope_candidates", []):
                scope_counts[scope] += 1

        matrix[corridor] = {
            "jurisdictions": sorted(jurisdictions),
            "candidate_unit_count": len(relevant),
            "scope_candidate_counts": dict(scope_counts),
            "applicability_proven": False,
            "reason": (
                "Jurisdiction overlap is discovery evidence only. "
                "Product, HS code, destination, effective date and legal scope "
                "must be independently validated."
            )
        }

    return matrix


def detect_conflicts(
    groups: list[dict[str, Any]],
    units_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:

    conflicts = []

    for group in groups:
        members = [
            units_by_id[unit_id]
            for unit_id in group["unit_ids"]
            if unit_id in units_by_id
        ]

        if len(members) < 2:
            continue

        normalized = {
            normalize_text(member.get("text", ""))
            for member in members
        }

        if len(normalized) <= 1:
            continue

        has_supersession_signal = bool(
            group["supersession_candidate_unit_ids"]
        )

        years = group.get("years", [])

        if has_supersession_signal or len(years) > 1:
            conflicts.append({
                "conflict_id": "CF-" + sha256_text(
                    group["group_id"] + ":"
                    + "|".join(sorted(normalized))
                )[:24],
                "group_id": group["group_id"],
                "unit_ids": group["unit_ids"],
                "years": years,
                "kind": (
                    "POSSIBLE_VERSION_OR_SUPERSESSION_CONFLICT"
                ),
                "status": "REVIEW_REQUIRED",
                "automatic_resolution": False,
                "legal_currentness_proven": False
            })

    return conflicts


def build_validation_cases(
    enriched_units: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    limit: int = 3000
) -> list[dict[str, Any]]:

    cases = []

    for unit in enriched_units:
        triage = unit["currentness_analysis"]["triage"]

        if triage not in {
            "SUPERSESSION_REVIEW_REQUIRED",
            "CURRENTNESS_REVIEW_REQUIRED",
            "STALE_RISK",
            "CURRENTNESS_UNKNOWN",
            "RECENT_DATE_CANDIDATE",
        }:
            continue

        prompt = (
            "LEGAL-CURRENTNESS VALIDATION CASE\n"
            f"Source: {unit.get('source_id')}\n"
            f"Jurisdiction: {unit.get('jurisdiction')}\n"
            f"Triage: {triage}\n"
            f"Candidate scopes: {unit.get('scope_candidates')}\n\n"
            f"Excerpt:\n{unit.get('text')}\n\n"
            "Determine what additional official evidence is required to establish: "
            "(1) document identity, (2) effective date, (3) whether amended/repealed/"
            "superseded, (4) exact jurisdiction, (5) product/HS scope, "
            "(6) destination/corridor applicability. "
            "Do NOT declare it current merely because the source is official."
        )

        cases.append({
            "case_id": "CUR-" + sha256_text(
                unit["unit_id"] + ":" + triage
            )[:24],
            "source_unit_id": unit["unit_id"],
            "variant": "legal_currentness",
            "prompt": prompt,
            "required_behaviour": {
                "allow_not_proven": True,
                "require_effective_date": True,
                "require_supersession_check": True,
                "require_scope_check": True,
                "require_official_provenance": True,
                "no_execution": True,
                "no_auto_canonical": True
            },
            "state": "DISCOVERED"
        })

        if len(cases) >= limit:
            break

    remaining = limit - len(cases)

    if remaining > 0:
        for conflict in conflicts[:remaining]:
            cases.append({
                "case_id": "CONFLICT-" + conflict["conflict_id"],
                "variant": "supersession_conflict",
                "conflict_id": conflict["conflict_id"],
                "unit_ids": conflict["unit_ids"],
                "prompt": (
                    "Resolve this possible legal version conflict using provenance "
                    "and official currentness evidence. Do not choose the newest-looking "
                    "text automatically. Determine whether one record amends, replaces, "
                    "coexists with, or is unrelated to the other."
                ),
                "required_behaviour": {
                    "no_guessing": True,
                    "no_newest_wins_heuristic": True,
                    "require_primary_source": True,
                    "no_execution": True,
                    "no_auto_canonical": True
                },
                "state": "DISCOVERED"
            })

    return cases


def invariant_audit(
    enriched_units: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    conflicts: list[dict[str, Any]]
) -> dict[str, Any]:

    violations = []

    for unit in enriched_units:
        if unit.get("legal_currentness_proven") is True:
            violations.append(
                f'{unit["unit_id"]}:LEGAL_CURRENTNESS_AUTO_PROVEN'
            )

        if unit.get("operational_applicability_proven") is True:
            violations.append(
                f'{unit["unit_id"]}:APPLICABILITY_AUTO_PROVEN'
            )

        if unit.get("execution_authority") is True:
            violations.append(
                f'{unit["unit_id"]}:EXECUTION_AUTHORITY_GRANTED'
            )

        if unit.get("canonical_promotion_allowed") is True:
            violations.append(
                f'{unit["unit_id"]}:CANONICAL_AUTO_PROMOTION'
            )

    for group in groups:
        if group.get("automatic_supersession_decision") is True:
            violations.append(
                f'{group["group_id"]}:AUTO_SUPERSESSION'
            )

    for conflict in conflicts:
        if conflict.get("automatic_resolution") is True:
            violations.append(
                f'{conflict["conflict_id"]}:AUTO_CONFLICT_RESOLUTION'
            )

    return {
        "violation_count": len(violations),
        "violations": violations,
        "pass": len(violations) == 0
    }


def main() -> int:

    snapshot = load_json(
        DATA / "official-source-snapshot.json"
    )

    raw_units_obj = load_json(
        DATA / "official-knowledge-units.json"
    )

    raw_units = raw_units_obj.get("units", [])

    enriched = build_enriched_units(
        raw_units,
        snapshot
    )

    by_id = {
        unit["unit_id"]: unit
        for unit in enriched
    }

    groups = build_candidate_groups(enriched)

    conflicts = detect_conflicts(
        groups,
        by_id
    )

    matrix = corridor_scope_matrix(enriched)

    validation_cases = build_validation_cases(
        enriched,
        groups,
        conflicts
    )

    audit = invariant_audit(
        enriched,
        groups,
        conflicts
    )

    triage_counts = collections.Counter(
        unit["currentness_analysis"]["triage"]
        for unit in enriched
    )

    scope_counts = collections.Counter(
        scope
        for unit in enriched
        for scope in unit.get("scope_candidates", [])
    )

    outputs = {
        DATA / "official-currentness-units.json": {
            "schema": "c5-foundry-currentness-units/v0.3",
            "generated_at": now_iso(),
            "unit_count": len(enriched),
            "triage_counts": dict(triage_counts),
            "scope_counts": dict(scope_counts),
            "units": enriched
        },

        DATA / "official-version-groups.json": {
            "schema": "c5-foundry-version-groups/v0.3",
            "generated_at": now_iso(),
            "group_count": len(groups),
            "groups": groups
        },

        DATA / "official-conflicts.json": {
            "schema": "c5-foundry-conflicts/v0.3",
            "generated_at": now_iso(),
            "conflict_count": len(conflicts),
            "conflicts": conflicts
        },

        DATA / "corridor-scope-matrix.json": {
            "schema": "c5-foundry-corridor-scope/v0.3",
            "generated_at": now_iso(),
            "corridors": matrix
        },

        CASES / "currentness-validation-cases.json": {
            "schema": "c5-foundry-currentness-cases/v0.3",
            "generated_at": now_iso(),
            "case_count": len(validation_cases),
            "cases": validation_cases
        },

        STATE / "v03-invariant-audit.json": {
            "schema": "c5-foundry-v03-invariant-audit/v0.3",
            "generated_at": now_iso(),
            **audit,
            "gl005_proven": False
        },
    }

    for path, payload in outputs.items():
        save_json(path, payload)

    hashes = {
        str(path.relative_to(ROOT)).replace("\\", "/"):
            sha256_bytes(path.read_bytes())
        for path in outputs
    }

    receipt = {
        "schema": "c5-foundry-currentness-receipt/v0.3",
        "generated_at": now_iso(),

        "metrics": {
            "source_unit_count": len(raw_units),
            "enriched_unit_count": len(enriched),
            "version_group_count": len(groups),
            "conflict_count": len(conflicts),
            "validation_case_count": len(validation_cases),
            "triage_counts": dict(triage_counts),
            "scope_counts": dict(scope_counts),
        },

        "hashes": hashes,

        "epistemic": {
            "CURRENTNESS_TRIAGE_ENGINE": True,
            "SUPERSESSION_CANDIDATE_ENGINE": True,
            "SCOPE_CLASSIFIER": True,
            "CORRIDOR_SCOPE_MATRIX": True,
            "CONFLICT_DETECTION": True,

            "LEGAL_CURRENTNESS_PROVEN": False,
            "OPERATIONAL_APPLICABILITY_PROVEN": False,
            "AUTO_SUPERSESSION_RESOLUTION": False,
            "AUTO_CANONICAL_PROMOTION": False,
            "REAL_EXPERT_EQUIVALENCE": False,
            "GL005_PROVEN": False,
        },

        "invariant_audit": audit,
    }

    receipt_path = (
        RECEIPTS
        / (
            "FOUNDRY-CURRENTNESS-"
            + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            + ".json"
        )
    )

    save_json(receipt_path, receipt)

    print(json.dumps({
        "success": audit["pass"],
        "source_units": len(raw_units),
        "enriched_units": len(enriched),
        "version_groups": len(groups),
        "conflicts": len(conflicts),
        "validation_cases": len(validation_cases),
        "invariant_violations": audit["violation_count"],
        "receipt": str(
            receipt_path.relative_to(ROOT)
        ).replace("\\", "/"),
        "legal_currentness_proven": False,
        "operational_applicability_proven": False,
        "auto_canonical_promotion": False,
        "gl005_proven": False,
    }, ensure_ascii=False, indent=2))

    return 0 if audit["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
