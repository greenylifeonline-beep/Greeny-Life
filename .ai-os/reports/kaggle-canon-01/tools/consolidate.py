#!/usr/bin/env python3
"""Deterministic Kaggle canonical consolidation (local merge + archive). No GPU."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\kaggle-canon-01")
BASE_REF = "greenylife/notebook8c2d6a9080"
DONOR_REF = "greenylife/notebook8d96bf4e18"
CANON_NB_REF = "greenylife/raios-canonical-workbench"
CANON_DS_REF = "greenylife/raios-canonical-estate"
DS_SLUGS = [
    "raios-greeny-continuity-evidence",
    "collection-for-understand",
    "raios-version-evidence",
    "greeny-life",
    "raios-cognitive-state",
]
PATH_MAP = {
    "/kaggle/input/raios-cognitive-state": "/kaggle/working/RAIOS-CANONICAL-ESTATE/sources/raios-cognitive-state",
    "/kaggle/input/raios-greeny-continuity-evidence": "/kaggle/working/RAIOS-CANONICAL-ESTATE/sources/raios-greeny-continuity-evidence",
    "/kaggle/input/collection-for-understand": "/kaggle/working/RAIOS-CANONICAL-ESTATE/sources/collection-for-understand",
    "/kaggle/input/raios-version-evidence": "/kaggle/working/RAIOS-CANONICAL-ESTATE/sources/raios-version-evidence",
    "/kaggle/input/greeny-life": "/kaggle/working/RAIOS-CANONICAL-ESTATE/sources/greeny-life",
}
RISK_RULES = [
    ("DELETE", [r"\bos\.remove\b", r"\bshutil\.rmtree\b", r"\brm\s+-rf", r"kaggle\s+datasets\s+delete", r"kaggle\s+kernels\s+delete"]),
    ("GIT_WRITE", [r"\bgit\s+push\b", r"\bgit\s+commit\b", r"\bgit\s+reset\b"]),
    ("KAGGLE_WRITE", [r"kaggle\s+datasets\s+create", r"kaggle\s+datasets\s+version", r"kaggle\s+kernels\s+push"]),
    ("TRAINING", [r"\.fit\s*\(", r"\bTrainer\b", r"\btrain_model\b", r"\bnum_train\b"]),
    ("MODEL", [r"\bollama\b", r"\btransformers\b", r"\btorch\.load", r"\bAutoModel", r"\bopenai\b", r"\bChatGroq", r"\bqwen3\b"]),
    ("NETWORK", [r"\brequests\.", r"\burllib\.", r"\bhttpx\.", r"\burlopen\b", r"\bsocket\."]),
    ("MUTATING", [r"open\([^)]*['\"][wa]", r"\bPath\([^)]*\)\.write", r"\bos\.system\b", r"\bsubprocess\."]),
    ("COSTLY", [r"\btorch\.cuda\b", r"\benable_gpu", r"\bcuda\b", r"while\s+True"]),
]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cell_source(cell) -> str:
    src = cell.source
    if isinstance(src, list):
        return "".join(src)
    return src or ""


def raw_sha(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def norm_text(text: str) -> str:
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def classify_risk(cell_type: str, text: str) -> str:
    if cell_type != "code":
        return "SAFE"
    if not text.strip():
        return "SAFE"
    for risk, pats in RISK_RULES:
        for p in pats:
            if re.search(p, text, re.I):
                return risk
    return "SAFE"


def wrap_nonsafe(text: str, risk: str, origin: str, idx: int) -> str:
    body = text if text.endswith("\n") else text + "\n"
    indented = "".join(("    " + ln if ln.strip() else ln) for ln in body.splitlines(True))
    skip = json.dumps(f"SKIPPED non-SAFE cell {risk} {origin}[{idx}]")
    return (
        f"# RAIOS_CELL_GUARD risk={risk} source={origin} index={idx}\n"
        "if globals().get('RAIOS_EXECUTE_NONSAFE', False):\n"
        f"{indented}"
        "else:\n"
        f"    print({skip})\n"
    )


def rewrite_paths(text: str, origin: str, idx: int, rewrites: list) -> str:
    out = text
    for old, new in PATH_MAP.items():
        if old in out:
            count = out.count(old)
            out = out.replace(old, new)
            rewrites.append(
                {
                    "SOURCE_NOTEBOOK": origin,
                    "SOURCE_CELL_INDEX": idx,
                    "FROM": old,
                    "TO": new,
                    "OCCURRENCES": count,
                }
            )
    return out


BOOTSTRAP = r'''# RAIOS canonical bootstrap — SAFE MODE. No GPU. No model.
from pathlib import Path
import hashlib, json, zipfile, sys

RAIOS_SAFE_MODE = True
RAIOS_INITIAL_CANONICAL_RUN = True
RAIOS_EXECUTE_NONSAFE = False

INPUT = Path("/kaggle/input")
WORKING = Path("/kaggle/working")
ZIP_NAME = "RAIOS-CANONICAL-ESTATE.zip"
ESTATE_NAME = "RAIOS-CANONICAL-ESTATE"

cands = list(INPUT.glob("**/RAIOS-CANONICAL-ESTATE.zip"))
if not cands:
    cands = list(WORKING.glob("**/RAIOS-CANONICAL-ESTATE.zip"))
if not cands:
    raise SystemExit("CANONICAL_ZIP_NOT_FOUND")
zip_path = cands[0]
print("CANONICAL_ZIP", zip_path)

dest = WORKING / ESTATE_NAME
dest.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(zip_path) as zf:
    zf.extractall(WORKING)

root_candidates = [WORKING / ESTATE_NAME]
if not (WORKING / ESTATE_NAME / "MANIFEST.json").exists():
    nested = list(WORKING.glob("**/RAIOS-CANONICAL-ESTATE/MANIFEST.json"))
    if nested:
        dest = nested[0].parent

RAIOS_EST_ROOT = dest
print("RAIOS_EST_ROOT", RAIOS_EST_ROOT)

manifest_hashes = RAIOS_EST_ROOT / "FILES-SHA256.txt"
if not manifest_hashes.exists():
    raise SystemExit("FILES_SHA256_MISSING")
expected = {}
for line in manifest_hashes.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    digest, rel = line.split("  ", 1)
    expected[rel.replace("\\", "/")] = digest

actual = {}
for p in sorted(RAIOS_EST_ROOT.rglob("*")):
    if p.is_file() and p.name != "FILES-SHA256.txt":
        rel = p.relative_to(RAIOS_EST_ROOT).as_posix()
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        actual[rel] = h.hexdigest()

missing = sorted(set(expected) - set(actual))
extra = sorted(set(actual) - set(expected))
mismatch = sorted(k for k in expected if k in actual and expected[k] != actual[k])
print("ZIP_EXTRACT_MISSING", len(missing))
print("ZIP_EXTRACT_EXTRA", len(extra))
print("ZIP_EXTRACT_MISMATCH", len(mismatch))
if missing or extra or mismatch:
    raise SystemExit("EXTRACTED_HASH_SET_EQUAL=false")
print("EXTRACTED_HASH_SET_EQUAL=true")

if RAIOS_INITIAL_CANONICAL_RUN:
    print("SAFE MODE: historical cells preserved and not executed.")
    raise SystemExit(0)
'''


def freeze_sources():
    recs = []
    files = []
    files += list((ROOT / "sources" / "nb-base").glob("*"))
    files += list((ROOT / "sources" / "nb-donor").glob("*"))
    for slug in DS_SLUGS:
        d = ROOT / "sources" / "datasets" / slug
        if not d.exists():
            raise SystemExit(f"DATASET_DIR_MISSING:{slug}")
        zips = list(d.glob("*.zip"))
        if not zips:
            raise SystemExit(f"DATASET_ZIP_MISSING:{slug}")
        files += zips
        meta = d / "dataset-metadata.json"
        if meta.exists():
            files.append(meta)
    for p in files:
        if p.is_file():
            recs.append(
                {
                    "PATH": str(p),
                    "REL": p.relative_to(ROOT).as_posix(),
                    "SIZE": p.stat().st_size,
                    "SHA256": sha256_file(p),
                }
            )
    obj = {
        "schema": "raios.kaggle.source-acquisition-freeze.v1",
        "generated_at": utcnow(),
        "SOURCE_NOTEBOOKS_ACQUIRED": 2,
        "SOURCE_DATASETS_ACQUIRED": 5,
        "files": recs,
    }
    dump(ROOT / "SOURCE-ACQUISITION-FREEZE.json", obj)
    return obj


def merge_notebooks():
    import nbformat
    from nbformat.v4 import new_code_cell, new_notebook

    base_path = ROOT / "sources" / "nb-base" / "notebook8c2d6a9080.ipynb"
    donor_path = ROOT / "sources" / "nb-donor" / "notebook8d96bf4e18.ipynb"
    base = nbformat.read(base_path, as_version=4)
    donor = nbformat.read(donor_path, as_version=4)

    lineage = []
    conflicts = []
    rewrites = []
    emitted_meta = []
    emitted_cells = []
    raw_index = {}
    norm_index = {}
    stats = {
        "BASE_CELLS": len(base.cells),
        "DONOR_CELLS": len(donor.cells),
        "EXACT_DUPLICATE_CELLS": 0,
        "NORMALIZED_DUPLICATE_CELLS": 0,
        "UNIQUE_BASE_CELLS": 0,
        "UNIQUE_DONOR_CELLS": 0,
        "CELL_CONFLICTS": 0,
        "UNACCOUNTED_CELLS": 0,
    }

    def similar_to_emitted(nt: str, nsha: str, ctype: str) -> int | None:
        for meta in emitted_meta:
            if meta["CELL_TYPE"] != ctype:
                continue
            if meta["NORMALIZED_SHA256"] == nsha:
                return meta["CANONICAL_INDEX"]
            ratio = SequenceMatcher(None, nt, meta["NORMALIZED_TEXT"]).ratio()
            if ratio >= 0.85 and ratio < 1.0:
                return meta["CANONICAL_INDEX"]
        return None

    def ingest(cell, origin: str, idx: int, unique_key: str):
        text0 = cell_source(cell)
        rsha = raw_sha(text0)
        ntxt = norm_text(text0)
        nsha = raw_sha(ntxt)
        ctype = cell.cell_type
        rec = {
            "SOURCE_NOTEBOOK": origin,
            "SOURCE_CELL_INDEX": idx,
            "CELL_TYPE": ctype,
            "RAW_SHA256": rsha,
            "NORMALIZED_SHA256": nsha,
        }
        if rsha in raw_index:
            rec["MERGE"] = "EXACT_DUPLICATE"
            rec["CANONICAL_INDEX"] = raw_index[rsha]
            lineage.append(rec)
            stats["EXACT_DUPLICATE_CELLS"] += 1
            emitted_meta[raw_index[rsha]]["PROVENANCE"].append(
                {"SOURCE_NOTEBOOK": origin, "SOURCE_CELL_INDEX": idx}
            )
            return
        if nsha in norm_index:
            rec["MERGE"] = "NORMALIZED_DUPLICATE"
            rec["CANONICAL_INDEX"] = norm_index[nsha]
            lineage.append(rec)
            stats["NORMALIZED_DUPLICATE_CELLS"] += 1
            emitted_meta[norm_index[nsha]]["PROVENANCE"].append(
                {"SOURCE_NOTEBOOK": origin, "SOURCE_CELL_INDEX": idx}
            )
            return

        rewritten = rewrite_paths(text0, origin, idx, rewrites)
        risk = classify_risk(ctype, rewritten)
        final_src = rewritten
        if ctype == "code" and risk != "SAFE":
            final_src = wrap_nonsafe(rewritten, risk, origin, idx)

        new_cell = deepcopy(cell)
        new_cell.source = final_src
        if hasattr(new_cell, "execution_count"):
            new_cell.execution_count = None
        if hasattr(new_cell, "outputs"):
            new_cell.outputs = []
        metadata = dict(getattr(new_cell, "metadata", {}) or {})
        metadata["raios"] = {
            "SOURCE_NOTEBOOK": origin,
            "SOURCE_CELL_INDEX": idx,
            "RISK": risk,
        }
        new_cell.metadata = metadata

        conflict_with = similar_to_emitted(ntxt, nsha, ctype)
        merge_class = unique_key
        if conflict_with is not None:
            merge_class = "CONFLICT_BOTH_PRESERVED"
            conflicts.append(
                {
                    "NEW_SOURCE": origin,
                    "NEW_INDEX": idx,
                    "EXISTING_CANONICAL_INDEX": conflict_with,
                    "NOTE": "similar-but-different; both preserved; no timestamp auto-resolve",
                }
            )
            stats["CELL_CONFLICTS"] += 1

        cidx = len(emitted_cells)
        emitted_cells.append(new_cell)
        emitted_meta.append(
            {
                "CANONICAL_INDEX": cidx,
                "CELL_TYPE": ctype,
                "RAW_SHA256": rsha,
                "NORMALIZED_SHA256": nsha,
                "NORMALIZED_TEXT": ntxt,
                "RISK": risk,
                "MERGE": merge_class,
                "PROVENANCE": [{"SOURCE_NOTEBOOK": origin, "SOURCE_CELL_INDEX": idx}],
            }
        )
        raw_index[rsha] = cidx
        norm_index[nsha] = cidx
        rec["MERGE"] = merge_class
        rec["CANONICAL_INDEX"] = cidx
        rec["RISK"] = risk
        lineage.append(rec)
        stats[unique_key] += 1

    for i, cell in enumerate(base.cells):
        ingest(cell, BASE_REF, i, "UNIQUE_BASE_CELLS")
    for i, cell in enumerate(donor.cells):
        ingest(cell, DONOR_REF, i, "UNIQUE_DONOR_CELLS")

    accounted = {(x["SOURCE_NOTEBOOK"], x["SOURCE_CELL_INDEX"]) for x in lineage}
    expected = {(BASE_REF, i) for i in range(len(base.cells))} | {
        (DONOR_REF, i) for i in range(len(donor.cells))
    }
    unaccounted = sorted(expected - accounted)
    stats["UNACCOUNTED_CELLS"] = len(unaccounted)

    boot = new_code_cell(BOOTSTRAP)
    boot.metadata = {"raios": {"ROLE": "CANONICAL_BOOTSTRAP", "RISK": "SAFE"}}
    all_cells = [boot] + emitted_cells
    nb = new_notebook(cells=all_cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "raios": {
            "CANONICAL": True,
            "SAFE_MODE": True,
            "enable_gpu": False,
            "dataset_sources": [CANON_DS_REF],
            "BASE": BASE_REF,
            "DONOR": DONOR_REF,
        },
    })
    out_nb = ROOT / "publish" / "notebook" / "raios-canonical-workbench.ipynb"
    out_nb.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, out_nb)
    src_sha = sha256_file(out_nb)

    merge_manifest = {
        "schema": "raios.kaggle.notebook-merge-manifest.v1",
        "generated_at": utcnow(),
        "NOTEBOOK_BASE": BASE_REF,
        "NOTEBOOK_DONOR": DONOR_REF,
        "CANONICAL_NOTEBOOK": CANON_NB_REF,
        **stats,
        "CANONICAL_CELLS": len(all_cells),
        "BOOTSTRAP_CELLS": 1,
        "SOURCE_NOTEBOOK_CELL_COVERAGE_PCT": 100.0 if not unaccounted else round(
            100.0 * (1 - len(unaccounted) / max(1, len(expected))), 4
        ),
        "UNACCOUNTED_SOURCE_CELLS": unaccounted,
        "CANONICAL_NOTEBOOK_SOURCE_SHA256": src_sha,
        "NO_GPU": True,
        "SAFE_MODE": True,
    }
    dump(ROOT / "NOTEBOOK-MERGE-MANIFEST.json", merge_manifest)
    dump(ROOT / "CELL-LINEAGE.json", {"schema": "raios.kaggle.cell-lineage.v1", "cells": lineage, "canonical": [
        {k: v for k, v in m.items() if k != "NORMALIZED_TEXT"} for m in emitted_meta
    ]})
    dump(ROOT / "CELL-CONFLICTS.json", {"schema": "raios.kaggle.cell-conflicts.v1", "conflicts": conflicts})
    dump(ROOT / "PATH-REWRITE-MANIFEST.json", {"schema": "raios.kaggle.path-rewrite.v1", "rewrites": rewrites})
    stats["CANONICAL_CELLS"] = len(all_cells)
    stats["CANONICAL_NOTEBOOK_SOURCE_SHA256"] = src_sha
    return merge_manifest


def merge_datasets():
    estate = ROOT / "canonical" / "RAIOS-CANONICAL-ESTATE"
    src_root = estate / "sources"
    prov = estate / "provenance"
    if estate.exists():
        shutil.rmtree(estate)
    src_root.mkdir(parents=True)
    prov.mkdir(parents=True)

    source_files = []
    for slug in DS_SLUGS:
        d = ROOT / "sources" / "datasets" / slug
        zips = list(d.glob("*.zip"))
        zpath = zips[0]
        dest = src_root / slug
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if name.endswith("/"):
                    continue
                data = zf.read(info)
                # prevent zip-slip
                target = dest / name
                target.resolve().relative_to(dest.resolve())
                parent_s = "\\?\\" + str(target.parent.resolve())
                os.makedirs(parent_s, exist_ok=True)
                dest_s = "\\?\\" + str(target.resolve())
                if os.path.exists(dest_s):
                    raise SystemExit(f"ZIP_MEMBER_COLLISION:{slug}:{name}")
                with open(dest_s, "wb") as fh:
                    fh.write(data)
                rel_in_ds = name
                source_files.append(
                    {
                        "SOURCE_DATASET": f"greenylife/{slug}",
                        "SOURCE_PATH": rel_in_ds,
                        "SIZE": len(data),
                        "SHA256": sha256_bytes(data),
                        "CANONICAL_PATH": f"sources/{slug}/{rel_in_ds}",
                    }
                )

    hash_groups = defaultdict(list)
    path_groups = defaultdict(list)
    for row in source_files:
        hash_groups[row["SHA256"]].append(row)
        rel = row["SOURCE_PATH"]
        path_groups[rel].append(row)

    for row in source_files:
        hmates = hash_groups[row["SHA256"]]
        pmates = path_groups[row["SOURCE_PATH"]]
        same_path_diff = [
            x for x in pmates if x["SHA256"] != row["SHA256"] and x["SOURCE_DATASET"] != row["SOURCE_DATASET"]
        ]
        if len(pmates) > 1 and all(x["SHA256"] == row["SHA256"] for x in pmates):
            row["CLASS"] = "SAME_PATH_SAME_CONTENT" if len({x["SOURCE_DATASET"] for x in pmates}) > 1 else "UNIQUE"
        elif same_path_diff:
            row["CLASS"] = "SAME_PATH_DIFFERENT_CONTENT"
        elif len(hmates) > 1:
            row["CLASS"] = "BYTE_EXACT_DUPLICATE"
        else:
            row["CLASS"] = "UNIQUE"

    dup_groups = [
        {"SHA256": h, "COUNT": len(v), "MEMBERS": v}
        for h, v in hash_groups.items()
        if len(v) > 1
    ]
    path_conflicts = []
    for rel, v in path_groups.items():
        hashes = {x["SHA256"] for x in v}
        datasets = {x["SOURCE_DATASET"] for x in v}
        if len(datasets) > 1 and len(hashes) > 1:
            path_conflicts.append({"SOURCE_PATH": rel, "MEMBERS": v})

    # hash every estate file except FILES-SHA256 which is written next
    estate_files = []
    for p in sorted(estate.rglob("*")):
        if p.is_file():
            rel = p.relative_to(estate).as_posix()
            estate_files.append((rel, sha256_file(p), p.stat().st_size))

    lines = [f"{h}  {rel}" for rel, h, _ in estate_files]
    (estate / "FILES-SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "schema": "raios.kaggle.canonical-estate.manifest.v1",
        "generated_at": utcnow(),
        "CANONICAL_DATASET": CANON_DS_REF,
        "SOURCE_DATASETS": 5,
        "SOURCE_FILES_TOTAL": len(source_files),
        "UNIQUE_FILE_HASHES": len(hash_groups),
        "EXACT_DUPLICATE_FILES": sum(1 for r in source_files if r["CLASS"] == "BYTE_EXACT_DUPLICATE"),
        "PATH_CONFLICTS": len(path_conflicts),
        "CANONICAL_FILES": len(estate_files) + 1,
        "UNACCOUNTED_FILES": 0,
        "NO_TIMESTAMP_AUTO_RESOLVE": True,
    }
    dump(estate / "MANIFEST.json", manifest)
    dump(prov / "SOURCE-DATASETS.json", {
        "datasets": [f"greenylife/{s}" for s in DS_SLUGS],
        "NOTE": "Namespaced under sources/<slug>/; original relative paths preserved",
    })
    dump(prov / "FILE-LINEAGE.json", {"files": source_files})
    dump(prov / "DUPLICATE-GROUPS.json", {"groups": dup_groups})
    dump(prov / "CONFLICTS.json", {"path_conflicts": path_conflicts})
    (estate / "README.md").write_text(
        "# RAIOS-CANONICAL-ESTATE\n\n"
        "Canonical merge of five Kaggle datasets. Sources preserved under `sources/<dataset>/`.\n"
        "Historical notebook TASKS/LOCKS/CURRENT-STATE are not current operational truth.\n"
        "Do not copy blindly into live RAIOS runtime.\n",
        encoding="utf-8",
    )

    # rewrite FILES-SHA256 to include MANIFEST/README/provenance after they exist
    estate_files = []
    for p in sorted(estate.rglob("*")):
        if p.is_file() and p.name != "FILES-SHA256.txt":
            rel = p.relative_to(estate).as_posix()
            estate_files.append((rel, sha256_file(p), p.stat().st_size))
    (estate / "FILES-SHA256.txt").write_text(
        "\n".join(f"{h}  {rel}" for rel, h, _ in estate_files) + "\n", encoding="utf-8"
    )
    manifest["CANONICAL_FILES"] = len(estate_files) + 1
    dump(estate / "MANIFEST.json", manifest)

    zip_path = ROOT / "canonical" / "RAIOS-CANONICAL-ESTATE.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(estate.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=f"RAIOS-CANONICAL-ESTATE/{p.relative_to(estate).as_posix()}")
    zip_ok = zipfile.ZipFile(zip_path).testzip() is None
    zip_sha = sha256_file(zip_path)

    verify = ROOT / "canonical" / "verify-extract"
    if verify.exists():
        shutil.rmtree(verify)
    verify.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(verify)
    extracted_root = verify / "RAIOS-CANONICAL-ESTATE"
    expected = {}
    for line in (extracted_root / "FILES-SHA256.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        expected[rel] = digest
    actual = {}
    for p in extracted_root.rglob("*"):
        if p.is_file() and p.name != "FILES-SHA256.txt":
            actual[p.relative_to(extracted_root).as_posix()] = sha256_file(p)
    equal = expected == actual

    sidecar_manifest = {
        "schema": "raios.kaggle.canonical-payload.v1",
        "generated_at": utcnow(),
        "CANONICAL_DATASET": CANON_DS_REF,
        "ZIP": str(zip_path),
        "ZIP_SHA256": zip_sha,
        "ZIP_SIZE": zip_path.stat().st_size,
        "ZIP_INTEGRITY_PASS": zip_ok,
        "EXTRACTED_HASH_SET_EQUAL": equal,
        **{k: manifest[k] for k in [
            "SOURCE_DATASETS", "SOURCE_FILES_TOTAL", "UNIQUE_FILE_HASHES",
            "EXACT_DUPLICATE_FILES", "PATH_CONFLICTS", "CANONICAL_FILES", "UNACCOUNTED_FILES",
        ]},
    }
    dump(ROOT / "canonical" / "RAIOS-CANONICAL-MANIFEST.json", sidecar_manifest)
    (ROOT / "canonical" / "RAIOS-CANONICAL-SHA256.txt").write_text(
        f"{zip_sha}  RAIOS-CANONICAL-ESTATE.zip\n", encoding="utf-8"
    )
    (ROOT / "canonical" / "README.md").write_text(
        "# RAIOS canonical estate payload\n\n"
        f"Dataset target: `{CANON_DS_REF}` (PRIVATE).\n"
        f"ZIP SHA256: `{zip_sha}`\n"
        f"ZIP_INTEGRITY_PASS={zip_ok}\n"
        f"EXTRACTED_HASH_SET_EQUAL={equal}\n",
        encoding="utf-8",
    )

    pub = ROOT / "publish" / "dataset"
    if pub.exists():
        shutil.rmtree(pub)
    pub.mkdir(parents=True)
    shutil.copy2(zip_path, pub / "RAIOS-CANONICAL-ESTATE.zip")
    shutil.copy2(ROOT / "canonical" / "RAIOS-CANONICAL-MANIFEST.json", pub / "RAIOS-CANONICAL-MANIFEST.json")
    shutil.copy2(ROOT / "canonical" / "RAIOS-CANONICAL-SHA256.txt", pub / "RAIOS-CANONICAL-SHA256.txt")
    shutil.copy2(ROOT / "canonical" / "README.md", pub / "README.md")
    dump(pub / "dataset-metadata.json", {
        "title": "raios-canonical-estate",
        "id": CANON_DS_REF,
        "licenses": [{"name": "CC0-1.0"}],
        "isPrivate": True,
        "keywords": ["raios", "greeny-life", "canonical"],
        "subtitle": "Canonical merge of five RAIOS Kaggle datasets",
        "description": "Private canonical estate. Sources namespaced. Not a live runtime.",
    })
    dump(ROOT / "publish" / "notebook" / "kernel-metadata.json", {
        "id": CANON_NB_REF,
        "title": "raios-canonical-workbench",
        "code_file": "raios-canonical-workbench.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "keywords": ["raios", "canonical", "safe-mode"],
        "dataset_sources": [CANON_DS_REF],
        "kernel_sources": [],
        "competition_sources": [],
        "model_sources": [],
    })
    return sidecar_manifest


def main():
    try:
        import nbformat  # noqa: F401
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nbformat", "--quiet"])
        import nbformat  # noqa: F401

    freeze = freeze_sources()
    nb = merge_notebooks()
    ds = merge_datasets()
    out = {
        "TASK_ID": "RAIOS-KAGGLE-CANONICAL-CONSOLIDATION-01",
        "generated_at": utcnow(),
        "freeze_files": len(freeze["files"]),
        "notebook": nb,
        "dataset": ds,
        "ZIP_INTEGRITY_PASS": ds["ZIP_INTEGRITY_PASS"],
        "EXTRACTED_HASH_SET_EQUAL": ds["EXTRACTED_HASH_SET_EQUAL"],
        "UNACCOUNTED_SOURCE_CELLS": nb["UNACCOUNTED_CELLS"],
        "UNACCOUNTED_SOURCE_FILES": ds["UNACCOUNTED_FILES"],
    }
    dump(ROOT / "LOCAL-CONSOLIDATION-RESULT.json", out)
    print(json.dumps(out, indent=2))
    if not ds["ZIP_INTEGRITY_PASS"] or not ds["EXTRACTED_HASH_SET_EQUAL"]:
        sys.exit(2)
    if nb["UNACCOUNTED_CELLS"] != 0:
        sys.exit(3)


if __name__ == "__main__":
    main()
