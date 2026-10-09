from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .cas_durability import publish_verified_copy, reconcile_publish_residue


AUTHORITY_DEFAULTS = {
    "storage_status": "STORED",
    "validation_status": "UNVALIDATED",
    "trust_status": "UNTRUSTED",
    "canonical_status": "NOT_CANONICAL",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _with_authority(entry: dict) -> dict:
    out = dict(entry)
    if out.get("status") == "IMPORTED":
        for key, value in AUTHORITY_DEFAULTS.items():
            out.setdefault(key, value)
    return out


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

    reconciliation = reconcile_publish_residue(cas)
    entries: list[dict] = []
    retained = 0
    if manifest.is_file():
        previous = json.loads(manifest.read_text(encoding="utf-8-sig"))
        for raw_item in previous.get("entries", []):
            item = _with_authority(raw_item)
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

    copied = 0
    reused = 0
    superseded: list[dict] = []

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

            keep: list[dict] = []
            for item in entries:
                same_logical_source = (
                    item.get("status") == "IMPORTED"
                    and item.get("donor") == donor.donor
                    and item.get("source_relative") == rel
                )
                if same_logical_source and item.get("source_sha256") != digest:
                    superseded.append(item)
                    retained = max(0, retained - 1)
                    continue
                keep.append(item)
            entries = keep

            existing = next(
                (
                    item
                    for item in entries
                    if item.get("status") == "IMPORTED"
                    and item.get("donor") == donor.donor
                    and item.get("source_relative") == rel
                    and item.get("source_sha256") == digest
                ),
                None,
            )
            if existing is not None:
                publish_verified_copy(source, Path(existing["object_path"]), expected_sha256=digest)
                reused += 1
                continue

            created = publish_verified_copy(source, object_path, expected_sha256=digest)
            if created:
                copied += 1
            else:
                reused += 1

            entries.append({
                "donor": donor.donor,
                "source_root": str(root),
                "source_relative": rel,
                "source_sha256": digest,
                "size_bytes": size,
                "object_path": str(object_path),
                "status": "IMPORTED",
                **AUTHORITY_DEFAULTS,
            })

    referenced_objects = {
        str(Path(str(item.get("object_path"))).resolve())
        for item in entries
        if item.get("status") == "IMPORTED" and item.get("object_path")
    }
    pending_delete: list[str] = []
    deleted_superseded: list[str] = []
    attempted: set[str] = set()
    for item in superseded:
        raw_path = str(item.get("object_path") or "")
        if not raw_path:
            continue
        obj = Path(raw_path)
        resolved = str(obj.resolve())
        if resolved in referenced_objects or resolved in attempted:
            continue
        attempted.add(resolved)
        if not obj.exists():
            continue
        try:
            obj.unlink()
            deleted_superseded.append(resolved)
        except OSError:
            pending_delete.append(resolved)

    unique_objects = {
        e["source_sha256"]
        for e in entries
        if e.get("status") == "IMPORTED"
    }
    total_bytes = sum(
        int(item.get("size_bytes") or 0)
        for item in entries
        if item.get("status") == "IMPORTED"
    )
    result = {
        "schema": "raios.factory-fabric.estate-import.v2",
        "generated_at": utc(),
        "runtime_root": str(runtime_root),
        "entries": entries,
        "source_file_count": sum(1 for e in entries if e.get("status") == "IMPORTED"),
        "unique_object_count": len(unique_objects),
        "objects_copied": copied,
        "objects_reused": reused,
        "retained_entries": retained,
        "source_bytes_indexed": total_bytes,
        "superseded_entry_count": len(superseded),
        "superseded_objects_deleted": deleted_superseded,
        "pending_delete_count": len(pending_delete),
        "pending_delete": pending_delete,
        "cas_reconciliation": reconciliation,
        "authority_axes": list(AUTHORITY_DEFAULTS),
        "source_mutation": False,
        "canonical_repo_mutation": False,
    }
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
        if item.get("storage_status", "STORED") != "STORED":
            continue
        rel = str(item.get("source_relative") or "")
        if Path(rel).name not in wanted:
            continue
        obj = Path(str(item.get("object_path")))
        key = item.get("source_sha256")
        if not obj.is_file() or key in seen:
            continue
        if sha256(obj) != key:
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
                    "authority": {
                        "storage_status": item.get("storage_status", "STORED"),
                        "validation_status": item.get("validation_status", "UNVALIDATED"),
                        "trust_status": item.get("trust_status", "UNTRUSTED"),
                        "canonical_status": item.get("canonical_status", "NOT_CANONICAL"),
                    },
                    "event": event,
                })
    return rows
