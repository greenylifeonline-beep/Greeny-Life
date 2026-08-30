"""Kaggle is a worker/cache. Session disks are not persistent cognitive truth."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class KaggleBackend:
    backend_id = "kaggle"
    category = "EPHEMERAL_SCRATCH"

    def classify(self) -> dict[str, Any]:
        on_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/working").exists()
        cred = (Path.home() / ".kaggle" / "kaggle.json").is_file() or bool(
            os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")
        )
        states = ["REFERENCED", "WORKER_CACHE"]
        if cred:
            states.append("AUTHENTICATED")
        else:
            states.append("BLOCKED_AUTH")
        if on_kaggle:
            states.extend(["READABLE", "WRITABLE"])
        states.append("CAPACITY_UNKNOWN" if not on_kaggle else "CAPACITY_KNOWN")
        return {
            "backend": self.backend_id,
            "category": self.category,
            "on_kaggle_session": on_kaggle,
            "credential_present": cred,
            "states": states,
            "role": "WORKER_CACHE",
            "durable_writable_state": False,
            "persistent_brain": False,
            "law": ["KAGGLE_NE_PERSISTENT_BRAIN", "WORKER_NE_C5", "ACCOUNT_CAPABILITY_NE_SESSION_GPU"],
        }

    def put(self, content: bytes, *, name: str) -> dict[str, Any]:
        working = Path("/kaggle/working")
        if not working.exists():
            return {"ok": False, "reason": "NOT_ON_KAGGLE", "durable": False}
        path = working / "raios-cache" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return {"ok": True, "path": str(path), "durable": False, "role": "WORKER_CACHE"}

    def get(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "KAGGLE_NOT_CONTENT_ADDRESSED_TRUTH", "object_id": object_id}

    def delete(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "KAGGLE_NOT_CONTENT_ADDRESSED_TRUTH", "object_id": object_id}
