from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAWBOOK = ROOT / ".ai-os" / "mcp" / "C5-MAINTENANCE-LAWS.json"


def load() -> dict[str, Any]:
    return json.loads(LAWBOOK.read_text(encoding="utf-8-sig"))


def maintenance_text(row: dict[str, Any]) -> str:
    parts = [
        f"LAW={row.get('id')}",
        f"INCIDENT={row.get('incident')}",
        f"ROOT_CAUSE={row.get('root_cause') or row.get('incident')}",
        f"DETECT={row.get('detect')}",
        f"GUARD={row.get('guard')}",
        f"REMEDIATION={row.get('remediation')}",
        f"NON_RECURRENCE={row.get('non_recurrence') or 'guard plus regression test must pass'}",
    ]
    return "\n".join(parts)


def assimilate_all() -> dict[str, Any]:
    from raios.c5_gateway.cognitive_loop import assimilate_turn, learning_root

    book = load()
    results: list[dict[str, Any]] = []
    for row in book.get("laws", []):
        law_id = str(row.get("id") or "UNKNOWN")
        prompt = f"RAIOS C5 maintenance lesson: {law_id}. Explain and retain the proven failure pattern."
        response = maintenance_text(row)
        result = assimilate_turn(
            prompt=prompt,
            response=response,
            conversation_id="C5-MAINTENANCE-CLOSURE",
            model="C1-AUTHORIZED-MAINTENANCE-EVIDENCE",
            grounding={"count": 1, "evidence_refs": [law_id]},
        )
        results.append({"law": law_id, **result})
    root = learning_root()
    return {
        "schema": "raios.c5-maintenance-assimilation.v1",
        "law_count": len(book.get("laws", [])),
        "results": results,
        "learning_root": str(root),
        "all_wal_clean": all(not bool(r.get("wal_written")) for r in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="raios-c5-assimilate-maintenance")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = assimilate_all()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    failed = [r for r in result["results"] if r.get("review_state") == "NEEDS_REVIEW"]
    return 0 if result["all_wal_clean"] and not failed else 24


if __name__ == "__main__":
    raise SystemExit(main())
