"""Structured cortex output. Invalid schema fails closed. No regex salvage."""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .config import FailClosed
from .schemas import CortexResponse


class StructuredInference:
    def parse(self, payload: Any) -> CortexResponse:
        if isinstance(payload, str):
            raise FailClosed("FREE_TEXT_NOT_STRUCTURE")
        try:
            rec = CortexResponse.model_validate(payload)
        except ValidationError as exc:
            raise FailClosed(f"INVALID_STRUCTURED_OUTPUT:{exc.error_count()}") from exc
        if rec.execution_authority or rec.canonical_authority:
            raise FailClosed("MODEL_OUTPUT_HAS_NO_AUTHORITY")
        return rec

    def from_ollama(self, body: dict[str, Any]) -> CortexResponse:
        if "assessment" in body:
            return self.parse(body)
        msg = body.get("message") or {}
        content = msg.get("content")
        if isinstance(content, dict):
            return self.parse(content)
        raise FailClosed("INVALID_STRUCTURED_OUTPUT:NO_OBJECT")
