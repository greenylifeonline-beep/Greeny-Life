from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .test_d059_contract import validate_pair


def load_evidence(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)

    data = json.loads(
        p.read_text(
            encoding="utf-8-sig",
        )
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(
            data.get("records"),
            list,
        ):
            return data["records"]

        records = []

        for family in ("qwen", "granite"):
            value = data.get(family)

            if isinstance(value, dict):
                record = dict(value)
                record.setdefault(
                    "family",
                    family,
                )
                records.append(record)

        if records:
            return records

    raise ValueError(
        "UNSUPPORTED_ASSIMILATION_EVIDENCE_SCHEMA"
    )


def validate_evidence_file(
    path: str | Path,
) -> dict[str, Any]:
    records = load_evidence(path)
    errors = validate_pair(records)

    return {
        "schema": "raios.d059.acceptance-result.v1",
        "records": records,
        "errors": errors,
        "accepted": not errors,
    }

