from __future__ import annotations

import os
import re
from pathlib import Path

from .identity import FailClosed

WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CONIN$",
    "CONOUT$",
    *[f"COM{i}" for i in range(1, 10)],
    *[f"LPT{i}" for i in range(1, 10)],
}

ADS_RE = re.compile(r":[^\\/]+$")


class PathSecurityError(FailClosed):
    pass


def _strip_ads(component: str) -> str:
    if ":" in component:
        raise PathSecurityError("ALTERNATE_DATA_STREAM_REJECTED")
    return component


def reject_unsafe_user_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise PathSecurityError("EMPTY_PATH")
    if "\x00" in raw:
        raise PathSecurityError("NUL_IN_PATH")
    text = raw.strip()
    if text.startswith("\\\\") or text.startswith("//") or text.lower().startswith("unc\\"):
        raise PathSecurityError("UNC_ESCAPE_REJECTED")
    if len(text) >= 2 and text[1] == ":" and text[0].isalpha():
        raise PathSecurityError("WINDOWS_DRIVE_ESCAPE_REJECTED")
    if text.startswith("/") or text.startswith("\\"):
        raise PathSecurityError("ABSOLUTE_PATH_REJECTED")
    if ":" in text:
        raise PathSecurityError("ALTERNATE_DATA_STREAM_REJECTED")
    return text


def normalize_scope(scope: str) -> str:
    text = reject_unsafe_user_path(scope)
    text = text.replace("\\", "/")
    parts: list[str] = []
    for raw_part in text.split("/"):
        part = raw_part.strip()
        if part in ("", "."):
            continue
        if part == "..":
            raise PathSecurityError("PATH_TRAVERSAL_REJECTED")
        stem = part.split(".")[0].upper()
        if stem in WINDOWS_RESERVED or part.upper() in WINDOWS_RESERVED:
            raise PathSecurityError("WINDOWS_RESERVED_NAME_REJECTED")
        _strip_ads(part)
        parts.append(part.lower())
    if not parts:
        raise PathSecurityError("EMPTY_PATH")
    return "/".join(parts)


def scopes_overlap(a: str, b: str) -> bool:
    left = normalize_scope(a)
    right = normalize_scope(b)
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def assert_contained(root: Path, relative: str) -> Path:
    """Resolve *relative* inside *root* without following escapes.

    Symlinks and Windows junctions/reparse points are rejected. os.path.basename
    is never used as the containment check.
    """
    rel = normalize_scope(relative)
    root_resolved = Path(os.path.normcase(str(root))).resolve()
    current = root_resolved
    for part in rel.split("/"):
        current = current / part
        if current.exists() and (current.is_symlink() or _is_reparse(current)):
            raise PathSecurityError("SYMLINK_OR_JUNCTION_ESCAPE_REJECTED")
    resolved = Path(os.path.normcase(str(current))).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSecurityError("PATH_TRAVERSAL_REJECTED") from exc
    if resolved.exists() and (resolved.is_symlink() or _is_reparse(resolved)):
        raise PathSecurityError("SYMLINK_OR_JUNCTION_ESCAPE_REJECTED")
    return resolved


def _is_reparse(path: Path) -> bool:
    try:
        st = path.lstat()
    except OSError:
        return False
    # Windows FILE_ATTRIBUTE_REPARSE_POINT often appears as symlink to pathlib.
    return bool(getattr(st, "st_file_attributes", 0) & 0x400)


def sha256_object_relpath(digest: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PathSecurityError("INVALID_CONTENT_DIGEST")
    return f"{digest[:2]}/{digest[2:4]}/{digest}"
