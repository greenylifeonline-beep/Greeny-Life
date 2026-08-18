from __future__ import annotations

ALLOWED_REF_PREFIXES = (
    "task://",
    "result://",
    "artifact://sha256/",
    "evidence://",
    "failure://",
    "experience://",
    "skill://",
)


class ExchangeRefError(ValueError):
    pass


def validate_exchange_ref(ref: str) -> str:
    if not isinstance(ref, str) or not ref:
        raise ExchangeRefError("EMPTY_EXCHANGE_REF")
    if not any(ref.startswith(prefix) for prefix in ALLOWED_REF_PREFIXES):
        raise ExchangeRefError(f"UNSUPPORTED_EXCHANGE_REF:{ref}")
    if ref.startswith("artifact://") and not ref.startswith("artifact://sha256/"):
        raise ExchangeRefError("ARTIFACT_REF_MUST_BE_CONTENT_ADDRESSED")
    return ref


def validate_refs(refs: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(validate_exchange_ref(ref) for ref in refs)
