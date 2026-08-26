# Strict JSON parse + duplicate-key scan for modified master artifacts.
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RUN = Path(
    r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\master-estate-census\RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z"
)


class DuplicateKeyError(ValueError):
    pass


def object_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise DuplicateKeyError(k)
        out[k] = v
    return out


def scan(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text, object_pairs_hook=object_pairs)
    except DuplicateKeyError as e:
        return {"path": str(path.relative_to(RUN)).replace("\\", "/"), "ok": False, "duplicate_key": str(e)}
    except json.JSONDecodeError as e:
        return {"path": str(path.relative_to(RUN)).replace("\\", "/"), "ok": False, "json_error": str(e)}
    n_surfaces = None
    if path.name == "01-MASTER-SURFACE-REGISTRY.json":
        n_surfaces = len(obj.get("surfaces") or [])
    return {"path": str(path.relative_to(RUN)).replace("\\", "/"), "ok": True, "surfaces": n_surfaces}


def main() -> None:
    files = sorted(p for p in RUN.rglob("*.json") if p.is_file())
    results = [scan(p) for p in files]
    fails = [r for r in results if not r["ok"]]
    dup_remaining = sum(1 for r in fails if "duplicate_key" in r)
    report = {
        "schema": "raios.json-strict-parse.v1",
        "TASK_ID": "RAIOS-KAGGLE-REGISTRY-NORMALIZATION-DELTA",
        "JSON_STRICT_PARSE_PASS": len(fails) == 0,
        "FILES_SCANNED": len(results),
        "DUPLICATE_KEYS_REMAINING": dup_remaining,
        "FAILURES": fails,
        "MASTER_SURFACES_TOTAL": next((r["surfaces"] for r in results if r.get("surfaces") is not None), None),
    }
    out = RUN / "cloud" / "kaggle" / "JSON-STRICT-PARSE.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # hash registry
    reg = RUN / "01-MASTER-SURFACE-REGISTRY.json"
    print(json.dumps(report, indent=2))
    print("REG_SHA", hashlib.sha256(reg.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
