"""Duplicate-group mining. Same SHA-256 is proven duplicate; names never decide."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .store import IndexStore


def duplicate_groups(store: IndexStore) -> list[dict[str, Any]]:
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in store.files():
        digest = rec.get("sha256")
        if not digest:
            continue
        by_hash[digest].append(
            {
                "file_id": rec.get("file_id"),
                "relative_path": rec.get("relative_path"),
                "root_id": rec.get("root_id"),
                "size": rec.get("size"),
            }
        )
    groups = []
    for digest, members in sorted(by_hash.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(members) < 2:
            continue
        groups.append(
            {
                "duplicate_group": digest,
                "sha256": digest,
                "count": len(members),
                "members": members,
                "state": "PROVEN",
                "confidence": 1.0,
                "evidence": "identical_sha256",
            }
        )
    return groups
