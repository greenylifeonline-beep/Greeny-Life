"""D10 Cursor/Copilot client probe. Observation only until D11 authorizes invocation."""
from __future__ import annotations

import os
import shutil
from typing import Any

from .config import utc_now


def probe_clients() -> dict[str, Any]:
    cursor_cli = shutil.which("cursor") or shutil.which("cursor-agent")
    copilot = shutil.which("gh") is not None
    env_hits = {k: bool(os.environ.get(k)) for k in (
        "CURSOR_AGENT",
        "CURSOR_TRACE_ID",
        "CURSOR_CLOUD_AGENT",
        "COMPOSER_SESSION_ID",
    )}
    present = bool(cursor_cli) or any(env_hits.values()) or Path_exists_agent()
    return {
        "cursor_cli": cursor_cli,
        "cursor_present": present,
        "copilot_gh_present": copilot,
        "env": env_hits,
        "invocation_authorized": False,
        "role": "GOVERNED_TEACHER_PROBE_ONLY",
        "created_at": utc_now(),
    }


def Path_exists_agent() -> bool:
    return bool(os.environ.get("CURSOR_AGENT") or os.path.exists("/opt/cursor") or os.path.exists("/home/ubuntu/.cursor"))


def governed_invoke(*_args: Any, **_kwargs: Any) -> None:
    from .config import FailClosed

    raise FailClosed("CURSOR_INVOCATION_FORBIDDEN_WITHOUT_D11")
