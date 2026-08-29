"""C2 all-hands bind. Reuses src/raios/a2a. Not a second bus or public agent surface."""

from .bind import (
    INTERNAL_SEATS,
    bind_c2,
    guarded_handle,
    routing_matrix,
    validate_envelope,
)

__all__ = [
    "INTERNAL_SEATS",
    "bind_c2",
    "guarded_handle",
    "routing_matrix",
    "validate_envelope",
]
