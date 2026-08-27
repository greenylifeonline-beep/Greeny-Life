"""Credential references and secret masking. Never embed tokens in the registry."""

from __future__ import annotations

import re
from typing import Any

SECRET_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "privatekey",
    "secret",
    "session_cookie",
    "cookie",
    "authorization",
    "bearer",
    "kaggle.json",
)

_HEXISH = re.compile(r"(?i)(sk-|ghp_|hf_|oci-|key-)[a-z0-9_\-]{8,}")
_BEARER = re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*")


def is_credential_ref(value: str) -> bool:
    prefixes = ("env:", "windows-credential-manager:", "file-ref:", "existing-receipt:", "existing:")
    return isinstance(value, str) and value.startswith(prefixes)


def looks_like_secret(value: Any) -> bool:
    if not isinstance(value, str) or len(value) < 12:
        return False
    if is_credential_ref(value):
        return False
    if "/" in value or "\\" in value or value.endswith((".json", ".py", ".md")):
        return False
    if _HEXISH.search(value) or _BEARER.search(value):
        return True
    return False


def mask_value(value: Any) -> Any:
    if looks_like_secret(value):
        return "***MASKED***"
    if isinstance(value, str) and any(f in value.lower() for f in ("password=", "token=")):
        return "***MASKED***"
    return value


def mask_record(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for key, val in obj.items():
            kl = str(key).lower()
            if any(frag in kl for frag in SECRET_KEY_FRAGMENTS):
                if isinstance(val, bool) or val in (None, "", "***MASKED***"):
                    out[key] = val
                elif isinstance(val, str) and is_credential_ref(val):
                    out[key] = val
                else:
                    out[key] = "***MASKED***"
            else:
                out[key] = mask_record(val)
        return out
    if isinstance(obj, list):
        return [mask_record(x) for x in obj]
    return mask_value(obj)


def assert_no_secrets(obj: Any, path: str = "$") -> None:
    if isinstance(obj, dict):
        for key, val in obj.items():
            kl = str(key).lower()
            if any(frag in kl for frag in SECRET_KEY_FRAGMENTS) and val not in (None, "", "***MASKED***"):
                if isinstance(val, bool):
                    continue
                if not (isinstance(val, str) and is_credential_ref(val)):
                    raise ValueError(f"SECRET_LEAK:{path}.{key}")
            assert_no_secrets(val, f"{path}.{key}")
        return
    if isinstance(obj, list):
        for i, val in enumerate(obj):
            assert_no_secrets(val, f"{path}[{i}]")
        return
    if looks_like_secret(obj):
        raise ValueError(f"SECRET_LEAK:{path}")
