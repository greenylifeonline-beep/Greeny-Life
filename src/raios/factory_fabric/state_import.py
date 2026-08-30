from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class DonorRoot:
    donor: str
    root: Path
    include_relative: frozenset[str] | None = None


def default_donors() -> tuple[DonorRoot, ...]:
    """Resolve optional donor roots without binding runtime to a retired tree."""
    configured: list[DonorRoot] = []
    raw = os.getenv("RAIOS_FACTORY_ESTATE_DONORS", "").strip()
    for item in filter(None, raw.split(os.pathsep)):
        if "=" not in item:
            continue
        name, path = item.split("=", 1)
        if name.strip() and path.strip():
            configured.append(DonorRoot(name.strip(), Path(path.strip())))
    configured.append(DonorRoot("c5-live-runtime", Path.home() / ".raios" / "runtime" / "c5"))
    return tuple(configured)


DEFAULT_DONORS = default_donors()


SKIP_NAMES = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", ".venv-multimodal"}


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_NAMES and not d.startswith(".venv")]
        current_path = Path(current)
        for name in files:
            p = current_path / name
            if p.is_file():
                yield p


def import_factory_estate(
    runtime_root: str | Path,
    donors: Iterable[DonorRoot] | None = None,
) -> dict:
    runtime_root = Path(runtime_root).expanduser().resolve()
    cas = runtime_root / "estate" / "objects"
    manifest_dir = runtime_root / "estate" / "manifests"
    manifest = manifest_dir / "FACTORY-ESTATE.json"
    cas.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    retained = 0
    if manifest.is_file():
        previous = json.loads(manifest.read_text(encoding="utf-8-sig"))
        for item in previous.get("entries", []):
            obj = Path(str(item.get("object_path") or ""))
            digest = str(item.get("source_sha256") or "")
            if (
                item.get("status") == "IMPORTED"
                and digest
                and obj.is_file()
                and obj.resolve().is_relative_to(cas)
                and sha256(obj) == digest
            ):
                entries.append(item)
                retained += 1

    known = {
        (item.get("donor"), item.get("source_relative"), item.get("source_sha256"))
        for item in entries
    }
    copied = 0
    reused = 0
    total_bytes = sum(int(item.get("size_bytes") or 0) for item in entries)

    for donor in default_donors() if donors is None else donors:
        root = donor.root.expanduser().resolve()
        if not root.exists():
            entries.append({
                "donor": donor.donor,
                "source_root": str(root),
                "status": "SOURCE_ROOT_MISSING",
            })
            continue

        for source in iter_files(root):
            rel = source.relative_to(root).as_posix()
            if donor.include_relative is not None and rel not in donor.include_relative:
                continue
            digest = sha256(source)
            size = source.stat().st_size
            suffix = source.suffix.lower() or ".bin"
            object_path = cas / f"{digest}{suffix}"
            key = (donor.donor, rel, digest)
            if key in known:
                reused += 1
                continue
            if object_path.exists():
                reused += 1
            else:
                shutil.copy2(source, object_path)
                copied += 1
            total_bytes += size
            entries.append({
                "donor": donor.donor,
                "source_root": str(root),
                "source_relative": rel,
                "source_sha256": digest,
                "size_bytes": size,
                "object_path": str(object_path),
                "status": "IMPORTED",
            })
            known.add(key)

    unique_objects = {
        e["source_sha256"]
        for e in entries
        if e.get("status") == "IMPORTED"
    }
    result = {
        "schema": "raios.factory-fabric.estate-import.v1",
        "generated_at": utc(),
        "runtime_root": str(runtime_root),
        "entries": entries,
        "source_file_count": sum(1 for e in entries if e.get("status") == "IMPORTED"),
        "unique_object_count": len(unique_objects),
        "objects_copied": copied,
        "objects_reused": reused,
        "retained_entries": retained,
        "source_bytes_indexed": total_bytes,
        "source_mutation": False,
        "canonical_repo_mutation": False,
    }
    manifest = manifest_dir / "FACTORY-ESTATE.json"
    manifest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result["manifest"] = str(manifest)
    return result


def load_imported_jsonl_events(runtime_root: str | Path) -> list[dict]:
    runtime_root = Path(runtime_root).expanduser().resolve()
    manifest = runtime_root / "estate" / "manifests" / "FACTORY-ESTATE.json"
    if not manifest.is_file():
        return []

    doc = json.loads(manifest.read_text(encoding="utf-8-sig"))
    rows: list[dict] = []
    wanted = {
        "training-events.jsonl",
        "engine-audit-experiences.jsonl",
        "execution-ledger.jsonl",
        "events.jsonl",
    }
    seen = set()
    for item in doc.get("entries", []):
        if item.get("status") != "IMPORTED":
            continue
        rel = str(item.get("source_relative") or "")
        if Path(rel).name not in wanted:
            continue
        obj = Path(str(item.get("object_path")))
        key = item.get("source_sha256")
        if not obj.is_file() or key in seen:
            continue
        seen.add(key)
        with obj.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                rows.append({
                    "donor": item.get("donor"),
                    "source_relative": rel,
                    "source_sha256": key,
                    "event": event,
                })
    return rows
