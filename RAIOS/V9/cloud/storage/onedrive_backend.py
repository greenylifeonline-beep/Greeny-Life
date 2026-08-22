"""OneDrive is a founder backup path, not a bound persistent brain on this VM."""
from __future__ import annotations

from typing import Any


class OneDriveBackend:
    backend_id = "onedrive"
    category = "BACKUP"

    def __init__(self, founder_path_count: int = 2) -> None:
        self.founder_path_count = int(founder_path_count)

    def classify(self) -> dict[str, Any]:
        return {
            "backend": self.backend_id,
            "category": self.category,
            "states": ["REFERENCED", "CAPACITY_UNKNOWN"],
            "founder_claimed_path_count": self.founder_path_count,
            "bound_on_this_host": False,
            "persistent_brain": False,
            "note": "Founder laptop claim only. This Cursor VM has no OneDrive mount.",
        }

    def put(self, content: bytes, *, name: str) -> dict[str, Any]:
        return {"ok": False, "reason": "ONEDRIVE_NOT_MOUNTED", "bytes": len(content), "name": name}

    def get(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "ONEDRIVE_NOT_MOUNTED", "object_id": object_id}

    def delete(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "ONEDRIVE_NOT_MOUNTED", "object_id": object_id}
