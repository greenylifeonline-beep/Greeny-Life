# Strict JSON parse + duplicate-key scan for Phase-1 master run.
# No network. No secrets. No Kaggle API.
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RUN = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\master-estate-census\RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z")
OUT = RUN / "cloud" / "kaggle" / "JSON-STRICT-PARSE.json"


class DuplicateKeyError(ValueError):
    pass


def make_hook(path: str, found: list):
    def hook(pairs):
        seen = {}
        dups = []
        for k, v in pairs:
            if k in seen:
                dups.append(k)
            seen[k] = v
        if dups:
            found.append({"path": path, "duplicate_keys": sorted(set(dups))})
            raise DuplicateKeyError(str(dups))
        return seen

    return hook


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    json_files = sorted(p for p in RUN.rglob("*.json") if p.is_file())
    failures = []
    dup_found = []
    parsed = 0
    for p in json_files:
        rel = str(p.relative_to(RUN)).replace("\\", "/")
        raw = p.read_text(encoding="utf-8")
        local_dups = []
        try:
            json.loads(raw, object_pairs_hook=make_hook(rel, local_dups))
            parsed += 1
        except DuplicateKeyError:
            failures.append({"path": rel, "error": "DUPLICATE_KEY", "keys": local_dups[-1]["duplicate_keys"] if local_dups else []})
            dup_found.extend(local_dups)
        except json.JSONDecodeError as e:
            failures.append({"path": rel, "error": "JSONDecodeError", "msg": str(e)})
        except OSError as e:
            failures.append({"path": rel, "error": type(e).__name__, "msg": str(e)})

    reg = RUN / "01-MASTER-SURFACE-REGISTRY.json"
    data = json.loads(reg.read_text(encoding="utf-8"))
    surfaces = data.get("surfaces") or []
    s58 = next(s for s in surfaces if s.get("SURFACE_ID") == "S58" or s.get("id") == "S58")
    evidence_keys_in_s58 = [k for k in s58.keys() if k == "EVIDENCE"]

    assets = json.loads((RUN / "cloud" / "kaggle" / "KAGGLE-NOTEBOOK-ASSETS.json").read_text(encoding="utf-8"))
    report = {
        "schema": "raios.json-strict-parse.v1",
        "TASK_ID": "RAIOS-KAGGLE-REGISTRY-NORMALIZATION-DELTA",
        "PARENT_TASK": "RAIOS-TOTAL-ESTATE-PHASE1-02",
        "JSON_STRICT_PARSE_PASS": len(failures) == 0,
        "FILES_SCANNED": len(json_files),
        "FILES_PARSED": parsed,
        "DUPLICATE_JSON_KEY_FOUND": len(dup_found) > 0,
        "DUPLICATE_KEYS_REMAINING": sum(len(x.get("duplicate_keys") or x.get("keys") or []) for x in (dup_found or failures)),
        "FAILURES": failures,
        "S58_EVIDENCE_KEY_COUNT": len(evidence_keys_in_s58),
        "S58_HAS_EVIDENCE_REFS": "EVIDENCE_REFS" in s58,
        "S58_STATUS": s58.get("STATUS") or s58.get("SURFACE_CLASS"),
        "S58_EVIDENCE_CLASS": s58.get("EVIDENCE_CLASS"),
        "S58_CHILD_ASSET_IDS": s58.get("CHILD_ASSET_IDS"),
        "MASTER_SURFACES_TOTAL": data.get("MASTER_SURFACES_TOTAL") or len(surfaces),
        "SURFACES_ARRAY_LEN": len(surfaces),
        "KAGGLE_NOTEBOOK_ASSETS_TOTAL": assets.get("KAGGLE_NOTEBOOK_ASSETS_TOTAL"),
        "REGISTRY_DELTA_SHA256": sha256_file(reg),
        "PREVIOUS_FROZEN_SHA256": data.get("PREVIOUS_MASTER_SURFACE_REGISTRY_SHA256"),
    }
    # Don't count keys listed twice in FAILURES+dup_found.
    report["DUPLICATE_KEYS_REMAINING"] = 0 if not dup_found and not any(f.get("error") == "DUPLICATE_KEY" for f in failures) else report["DUPLICATE_KEYS_REMAINING"]
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
