"""D9 Speculative / Idle recertification. Deterministic, bounded, no canonical writes."""
from __future__ import annotations

import sys
from typing import Any

from .config import FailClosed, contains_forbidden_success
from .process_kernel import encoding_safe_run
from .resource_governor import ResourceGovernor


class IdleRecertification:
    def __init__(self, governor: ResourceGovernor) -> None:
        self.governor = governor

    def recertify_encoding_and_false_pass(self) -> dict[str, Any]:
        if not self.governor.allow_background():
            return {"skipped": True, "reason": self.governor.mode}
        utf8 = encoding_safe_run([sys.executable, "-c", "print('idle-utf8')"])
        latin = encoding_safe_run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xe9')"])
        liar = encoding_safe_run([sys.executable, "-c", "print('PASS'); raise SystemExit(1)"])
        if utf8.returncode != 0:
            raise FailClosed("IDLE_RECERT_UTF8_FAILED")
        if latin.stdout is None:
            raise FailClosed("IDLE_RECERT_NONE_STDOUT")
        if liar.returncode == 0:
            raise FailClosed("IDLE_RECERT_LIAR_EXIT_ZERO")
        if contains_forbidden_success(liar.stdout) and liar.returncode != 0:
            status = "FALSE_PASS_BLOCKED"
        else:
            status = "CHILD_NONZERO"
        return {
            "skipped": False,
            "utf8_ok": True,
            "latin1_replaced": latin.decode_replaced,
            "liar_returncode": liar.returncode,
            "false_pass_blocked": status == "FALSE_PASS_BLOCKED",
            "canonical_mutation": False,
        }
