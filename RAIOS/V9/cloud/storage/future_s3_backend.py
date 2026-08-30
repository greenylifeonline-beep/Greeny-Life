"""Future S3/R2/B2 adapter. Absent until a real config exists. Do not invent credentials."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def detect_object_store_refs(root: Path) -> dict[str, Any]:
    names = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET", "R2_ACCOUNT_ID", "B2_KEY_ID", "SUPABASE_URL", "NEON_DATABASE_URL", "DATABASE_URL")
    env_present = {n: bool((os.environ.get(n) or "").strip()) for n in names}
    # values never returned
    files = []
    for rel in ("supabase", ".env", "configs/storage"):
        p = root / rel
        if p.exists():
            files.append(rel)
    any_secret_env = any(env_present.values())
    return {
        "env_flags_present": {k: v for k, v in env_present.items()},
        "path_refs": files,
        "any_live_object_store": False if not any_secret_env else "ENV_PRESENT_UNTESTED",
    }


class FutureS3Backend:
    backend_id = "future-s3"
    category = "OBJECT_STORAGE"

    def classify(self) -> dict[str, Any]:
        return {
            "backend": self.backend_id,
            "category": self.category,
            "states": ["ABSENT"],
            "persistent_brain": False,
            "note": "Placeholder. Do not bind architecture to one vendor.",
        }

    def put(self, content: bytes, *, name: str) -> dict[str, Any]:
        return {"ok": False, "reason": "S3_ABSENT", "name": name, "bytes": len(content)}

    def get(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "S3_ABSENT", "object_id": object_id}

    def delete(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "S3_ABSENT", "object_id": object_id}
