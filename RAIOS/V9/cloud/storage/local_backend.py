"""Local content-addressed store. Live-tested disposable artifacts. Not the brain."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .content_addressing import object_id
from .object_manifest import manifest_for


class LocalBackend:
    backend_id = "local"
    category = "EPHEMERAL_SCRATCH"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def classify(self) -> dict[str, Any]:
        return {
            "backend": self.backend_id,
            "category": self.category,
            "states": ["WRITABLE", "READABLE", "LIVE_TESTED", "CAPACITY_KNOWN"],
            "persistent_brain": False,
        }

    def put(self, content: bytes, *, name: str) -> dict[str, Any]:
        oid = object_id(content)
        path = self.root / oid
        path.write_bytes(content)
        man = manifest_for(content, name=name, provider=self.backend_id)
        return {"ok": True, "manifest": man.as_dict(), "path": str(path)}

    def get(self, oid: str) -> dict[str, Any]:
        path = self.root / oid
        if not path.is_file():
            return {"ok": False, "reason": "MISSING", "object_id": oid}
        data = path.read_bytes()
        return {"ok": True, "object_id": object_id(data), "bytes": len(data), "match": object_id(data) == oid}

    def delete(self, oid: str) -> dict[str, Any]:
        path = self.root / oid
        if path.is_file():
            path.unlink()
        return {"ok": True, "deleted": True, "exists_after": path.exists()}


def disposable_roundtrip(root: Path) -> dict[str, Any]:
    store = LocalBackend(root)
    payload = b"raios-disposable-storage-fabric-test"
    put = store.put(payload, name="receipts")
    oid = put["manifest"]["object_id"]
    got = store.get(oid)
    deleted = store.delete(oid)
    gone = store.get(oid)
    return {
        "ok": bool(got.get("ok") and got.get("match") and deleted.get("exists_after") is False and gone.get("ok") is False),
        "put": put,
        "get": got,
        "delete": deleted,
        "get_after_delete": gone,
        "backend": "local",
        "persistent_cognitive_storage_proven": False,
        "gl005_proven": False,
    }
