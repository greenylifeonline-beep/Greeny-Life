"""C1→C5 task-envelope dispatch. Wrap existing founder channel; do not replace chat."""

from .dispatch import dispatch, maybe_dispatch
from .envelope import SCHEMA_VERSION, looks_like_envelope

__all__ = ["SCHEMA_VERSION", "dispatch", "looks_like_envelope", "maybe_dispatch"]
