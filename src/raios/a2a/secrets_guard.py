"""Reject secret leakage in agent cards. Path/type only; never echo secret values."""

from __future__ import annotations

import json
import re
from typing import Any

from .failclosed import SECRET_LEAK_REJECTED, FailClosed

_KEY_HINTS = (
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "private_key",
    "privatekey",
    "begin rsa",
    "begin openssh",
    "authorization",
    "bearer ",
)

_PATH_HINTS = (
    r"c:\\users\\",
    r"/home/",
    r"\.kaggle\\credentials",
    r"id_rsa",
)


def scan_mapping(obj: Any, *, path: str = "$") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if any(h in lk for h in _KEY_HINTS):
                raise FailClosed(SECRET_LEAK_REJECTED, f"key:{path}.{k}")
            if isinstance(v, str) and _value_leaks(v):
                raise FailClosed(SECRET_LEAK_REJECTED, f"value:{path}.{k}")
            scan_mapping(v, path=f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_mapping(v, path=f"{path}[{i}]")
    elif isinstance(obj, str) and _value_leaks(obj):
        raise FailClosed(SECRET_LEAK_REJECTED, f"value:{path}")


def _value_leaks(text: str) -> bool:
    low = text.lower()
    if "begin rsa private" in low or "begin openssh private" in low:
        return True
    if re.search(r"sk-[a-z0-9]{16,}", low):
        return True
    return any(re.search(p, low) for p in _PATH_HINTS)


def scan_json_text(text: str) -> None:
    scan_mapping(json.loads(text))
