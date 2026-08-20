"""Adapter that exposes NeuroLingua as a GL-DOS intelligence capability.

Does not mutate Master Data. Does not replace GreenyLifeBrain. Mirrors
``unified-intelligence/adapters/intelligence-adapter.ts`` capability routing.
"""

from __future__ import annotations

from typing import Any

from raios.neuro_lingua.kernel import NeuroLingua, create_neuro_lingua
from raios.neuro_lingua.types import InterpretationContext


class NeuroLinguaCapability:
    name = "neuro_lingua.interpret"

    def __init__(self, kernel: NeuroLingua | None = None) -> None:
        self.kernel = kernel or create_neuro_lingua()

    async def execute(self, input_payload: dict[str, Any]) -> list[dict[str, Any]]:
        text = input_payload.get("text")
        if not text:
            return [{"code": "MISSING_TEXT"}]
        context = InterpretationContext.from_raw(input_payload.get("context"))
        result = await self.kernel.interpret(text=text, context=context)
        return [result.to_dict()]
