"""Localhost-only bind helper. Production public listen is forbidden."""

from __future__ import annotations

from .failclosed import PUBLIC_LISTENER_DISABLED, FailClosed
from .flags import A2A_PRODUCTION_ACTIVATED, A2A_PUBLIC_LISTENER_ENABLED


def assert_bind_allowed(host: str) -> None:
    if A2A_PRODUCTION_ACTIVATED or A2A_PUBLIC_LISTENER_ENABLED:
        raise FailClosed(PUBLIC_LISTENER_DISABLED, "production-activation")
    if host not in {"127.0.0.1", "localhost"}:
        raise FailClosed(PUBLIC_LISTENER_DISABLED, host)
