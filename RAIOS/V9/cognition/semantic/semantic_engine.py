from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"


# ---------------------------------------------------------------------
# Core epistemic primitives
# ---------------------------------------------------------------------

def clamp_confidence(value: Any) -> float:
    """
    Hard invariant:
    confidence must always be normalized to [0, 1].

    Values above 1 are rejected rather than silently treating 70 as 0.70.
    """
    if isinstance(value, bool):
        raise ValueError("BOOLEAN_IS_NOT_CONFIDENCE")

    try:
        value = float(value)
    except Exception as exc:
        raise ValueError("CONFIDENCE_NOT_NUMERIC") from exc

    if value < 0.0 or value > 1.0:
        raise ValueError(
            f"CONFIDENCE_OUT_OF_RANGE:{value}"
        )

    return round(value, 6)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO.resolve()))
    except Exception:
        return str(path)


def resolve_repo_path(value: str) -> Path:
    p = Path(value)

    if not p.is_absolute():
        p = REPO / p

    resolved = p.resolve()

    try:
        resolved.relative_to(REPO.resolve())
    except ValueError as exc:
        raise ValueError(
            "PATH_OUTSIDE_REPOSITORY"
        ) from exc

    return resolved


# ---------------------------------------------------------------------
# Authority / temporal classification
# ---------------------------------------------------------------------

def authority_profile(path: str) -> dict[str, Any]:
    p = path.replace("\\", "/").lower()

    if "raios/v9/continuity/raios-current-state.json" in p:
        return {
            "authority": "CURRENT_CANONICAL_STATE",
            "authority_rank": 100,
            "temporal_status": "CURRENT",
        }

    if "/canonical/" in f"/{p}":
        return {
            "authority": "CANONICAL_PROJECT_SOURCE",
            "authority_rank": 90,
            "temporal_status": "CURRENT_UNLESS_SUPERSEDED",
        }

    if "evidence/observations" in p:
        return {
            "authority": "CERTIFICATION_EVIDENCE",
            "authority_rank": 80,
            "temporal_status": "OBSERVATIONAL",
        }

    if "/archive/" in f"/{p}" or "historical" in p:
        return {
            "authority": "HISTORICAL_EVIDENCE",
            "authority_rank": 35,
            "temporal_status": "HISTORICAL",
        }

    if ".bak" in p or "backup" in p:
        return {
            "authority": "RECOVERY_PREIMAGE",
            "authority_rank": 30,
            "temporal_status": "HISTORICAL_OR_RECOVERY",
        }

    return {
        "authority": "WORKING_TREE_EVIDENCE",
        "authority_rank": 60,
        "temporal_status": "CURRENT_OBSERVATION",
    }


# ---------------------------------------------------------------------
# Evidence structures
# ---------------------------------------------------------------------

@dataclass
class EvidenceRef:
    evidence_id: str
    path: str
    sha256: str
    source_type: str
    authority: str
    authority_rank: int
    temporal_status: str
    locator: str
    excerpt: str


@dataclass
class Claim:
    claim_id: str
    subject: str
    predicate: str
    value: Any
    confidence: float
    evidence_refs: list[str]
    authority: str
    temporal_status: str
    status: str = "OBSERVED"


def make_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return f"{prefix}:{hashlib.sha256(raw).hexdigest()}"


# ---------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------

def read_artifact(path_value: str) -> dict[str, Any]:
    path = resolve_repo_path(path_value)

    if not path.exists():
        raise FileNotFoundError(
            f"ARTIFACT_NOT_FOUND:{path_value}"
        )

    if not path.is_file():
        raise ValueError(
            f"ARTIFACT_NOT_FILE:{path_value}"
        )

    raw = path.read_bytes()

    if len(raw) == 0:
        raise ValueError(
            f"ZERO_BYTE_ARTIFACT:{path_value}"
        )

    text = raw.decode(
        "utf-8-sig",
        errors="replace",
    )

    suffix = path.suffix.lower()

    parsed = None
    source_type = "TEXT"

    if suffix == ".json":
        source_type = "JSON"
        parsed = json.loads(text)

    elif suffix in {".md", ".markdown"}:
        source_type = "MARKDOWN"

    elif suffix in {
        ".py",".ts",".tsx",".js",".jsx",
        ".ps1",".yaml",".yml",".toml"
    }:
        source_type = "SOURCE_CODE"

    return {
        "path": relative(path),
        "absolute_path": str(path),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "source_type": source_type,
        "text": text,
        "parsed": parsed,
        "authority": authority_profile(relative(path)),
    }


# ---------------------------------------------------------------------
# JSON structural claim extraction
# ---------------------------------------------------------------------

def scalar(value: Any) -> bool:
    return (
        value is None
        or isinstance(
            value,
            (str, int, float, bool)
        )
    )


def walk_json(
    value: Any,
    prefix: str = "$",
):
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}"

            if scalar(child):
                yield (
                    child_prefix,
                    child,
                )
            else:
                yield from walk_json(
                    child,
                    child_prefix,
                )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"

            if scalar(child):
                yield (
                    child_prefix,
                    child,
                )
            else:
                yield from walk_json(
                    child,
                    child_prefix,
                )


def evidence_for_json_value(
    artifact: dict[str, Any],
    locator: str,
    value: Any,
) -> EvidenceRef:

    authority = artifact["authority"]

    payload = {
        "path": artifact["path"],
        "sha256": artifact["sha256"],
        "locator": locator,
        "value": value,
    }

    evidence_id = make_id(
        "evidence",
        payload,
    )

    excerpt = json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    )

    return EvidenceRef(
        evidence_id=evidence_id,
        path=artifact["path"],
        sha256=artifact["sha256"],
        source_type=artifact["source_type"],
        authority=authority["authority"],
        authority_rank=authority["authority_rank"],
        temporal_status=authority["temporal_status"],
        locator=locator,
        excerpt=excerpt[:500],
    )


def extract_json_claims(
    artifact: dict[str, Any],
) -> tuple[list[Claim], list[EvidenceRef]]:

    claims: list[Claim] = []
    evidence: list[EvidenceRef] = []

    authority = artifact["authority"]

    for locator, value in walk_json(
        artifact["parsed"]
    ):
        ev = evidence_for_json_value(
            artifact,
            locator,
            value,
        )

        evidence.append(ev)

        parts = locator.split(".")

        predicate = (
            parts[-1]
            if len(parts) > 1
            else locator
        )

        subject = artifact["path"]

        confidence = clamp_confidence(
            0.98
            if authority["authority_rank"] >= 80
            else 0.90
        )

        claim_payload = {
            "subject": subject,
            "predicate": predicate,
            "value": value,
            "evidence": ev.evidence_id,
        }

        claims.append(
            Claim(
                claim_id=make_id(
                    "claim",
                    claim_payload,
                ),
                subject=subject,
                predicate=predicate,
                value=value,
                confidence=confidence,
                evidence_refs=[
                    ev.evidence_id
                ],
                authority=
                    authority["authority"],
                temporal_status=
                    authority["temporal_status"],
            )
        )

    return claims, evidence


# ---------------------------------------------------------------------
# Text claim extraction
# ---------------------------------------------------------------------

SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?])\s+|\n+"
)


def extract_text_claims(
    artifact: dict[str, Any],
) -> tuple[list[Claim], list[EvidenceRef]]:

    claims: list[Claim] = []
    evidence: list[EvidenceRef] = []

    authority = artifact["authority"]

    sentences = [
        s.strip()
        for s in SENTENCE_SPLIT.split(
            artifact["text"]
        )
        if len(s.strip()) >= 20
    ]

    for index, sentence in enumerate(
        sentences[:500]
    ):
        locator = f"sentence:{index + 1}"

        evidence_id = make_id(
            "evidence",
            {
                "path": artifact["path"],
                "sha256": artifact["sha256"],
                "locator": locator,
                "text": sentence,
            },
        )

        ev = EvidenceRef(
            evidence_id=evidence_id,
            path=artifact["path"],
            sha256=artifact["sha256"],
            source_type=artifact["source_type"],
            authority=authority["authority"],
            authority_rank=authority[
                "authority_rank"
            ],
            temporal_status=authority[
                "temporal_status"
            ],
            locator=locator,
            excerpt=sentence[:500],
        )

        evidence.append(ev)

        confidence = clamp_confidence(
            0.80
            if authority["authority_rank"] >= 80
            else 0.68
        )

        claims.append(
            Claim(
                claim_id=make_id(
                    "claim",
                    {
                        "path": artifact["path"],
                        "sentence": sentence,
                    },
                ),
                subject=artifact["path"],
                predicate="states",
                value=sentence,
                confidence=confidence,
                evidence_refs=[
                    evidence_id
                ],
                authority=
                    authority["authority"],
                temporal_status=
                    authority["temporal_status"],
            )
        )

    return claims, evidence


# ---------------------------------------------------------------------
# Contradiction engine
# ---------------------------------------------------------------------

def normalize_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )


def detect_contradictions(
    claims: list[Claim],
) -> list[dict[str, Any]]:

    groups: dict[
        tuple[str, str],
        list[Claim]
    ] = {}

    for claim in claims:
        key = (
            claim.subject,
            claim.predicate,
        )

        groups.setdefault(
            key,
            [],
        ).append(claim)

    contradictions = []

    for key, group in groups.items():
        values = {
            normalize_value(c.value)
            for c in group
        }

        if len(values) <= 1:
            continue

        contradictions.append({
            "schema":
                "raios.contradiction.v1",

            "contradiction_id":
                make_id(
                    "contradiction",
                    {
                        "subject": key[0],
                        "predicate": key[1],
                        "claims": [
                            c.claim_id
                            for c in group
                        ],
                    },
                ),

            "subject": key[0],
            "predicate": key[1],

            "claim_refs": [
                c.claim_id
                for c in group
            ],

            "values": [
                c.value
                for c in group
            ],

            "status":
                "UNRESOLVED",

            "resolution_policy":
                "AUTHORITY_TEMPORAL_EVIDENCE_REQUIRED",
        })

    return contradictions


# ---------------------------------------------------------------------
# Main understanding
# ---------------------------------------------------------------------

def understand_artifact(
    path_value: str,
) -> dict[str, Any]:

    artifact = read_artifact(
        path_value
    )

    if artifact["source_type"] == "JSON":
        claims, evidence = \
            extract_json_claims(
                artifact
            )
    else:
        claims, evidence = \
            extract_text_claims(
                artifact
            )

    contradictions = \
        detect_contradictions(
            claims
        )

    unresolved_flags = []

    if contradictions:
        unresolved_flags.append(
            "CONTRADICTIONS_PRESENT"
        )

    if not claims:
        unresolved_flags.append(
            "NO_CLAIMS_EXTRACTED"
        )

    # Mandatory evidence invariant.
    for claim in claims:
        if not claim.evidence_refs:
            raise RuntimeError(
                "CLAIM_WITHOUT_EVIDENCE"
            )

        claim.confidence = \
            clamp_confidence(
                claim.confidence
            )

    result = {
        "schema":
            "raios.semantic-artifact.v1",

        "artifact": {
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "bytes": artifact["bytes"],
            "source_type":
                artifact["source_type"],
            **artifact["authority"],
        },

        "claim_count": len(claims),

        "evidence_count":
            len(evidence),

        "claims": [
            asdict(c)
            for c in claims
        ],

        "evidence": [
            asdict(e)
            for e in evidence
        ],

        "contradictions":
            contradictions,

        "unresolved_flags":
            unresolved_flags,

        "epistemic_status":
            "EVIDENCE_BOUNDED",

        "canonical_promotion":
            False,

        "abstention_required":
            bool(
                contradictions
                or not claims
            ),
    }

    return result


# ---------------------------------------------------------------------
# Multi-artifact comparison
# ---------------------------------------------------------------------

def compare_artifacts(
    paths: list[str],
) -> dict[str, Any]:

    if len(paths) < 2:
        raise ValueError(
            "COMPARE_REQUIRES_AT_LEAST_TWO_ARTIFACTS"
        )

    understood = [
        understand_artifact(p)
        for p in paths
    ]

    all_claims = []

    for item in understood:
        for raw in item["claims"]:
            all_claims.append(
                Claim(**raw)
            )

    cross_source = {}

    for claim in all_claims:
        key = claim.predicate

        cross_source.setdefault(
            key,
            [],
        ).append(claim)

    conflicts = []

    for predicate, group in \
        cross_source.items():

        if len(group) < 2:
            continue

        values = {
            normalize_value(
                c.value
            )
            for c in group
        }

        if len(values) <= 1:
            continue

        conflicts.append({
            "schema":
                "raios.cross-source-contradiction.v1",

            "predicate":
                predicate,

            "claims": [
                {
                    "claim_id":
                        c.claim_id,

                    "subject":
                        c.subject,

                    "value":
                        c.value,

                    "authority":
                        c.authority,

                    "temporal_status":
                        c.temporal_status,

                    "evidence_refs":
                        c.evidence_refs,
                }
                for c in group
            ],

            "status":
                "UNRESOLVED",

            "automatic_resolution":
                False,
        })

    return {
        "schema":
            "raios.semantic-comparison.v1",

        "artifact_count":
            len(understood),

        "artifacts":
            understood,

        "cross_source_contradictions":
            conflicts,

        "epistemic_status":
            "EVIDENCE_BOUNDED",

        "canonical_promotion":
            False,

        "abstention_required":
            bool(conflicts),
    }