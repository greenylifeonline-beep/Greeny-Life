"""NeuroLingua public API.

Usage::

    result = await neuro_lingua.interpret(text=text, context=context, target_locale=None)
    rendered = await neuro_lingua.realize(meaning=result.meaning, target_locale="nb-NO", context=context)
"""

from raios.neuro_lingua.kernel import NeuroLingua, create_neuro_lingua, interpret, realize
from raios.neuro_lingua.packet import CognitiveMeaningPacket, InterpretationResult, RenderedOutput
from raios.neuro_lingua.pipeline import PIPELINE_STAGES
from raios.neuro_lingua.types import INITIAL_LOCALES, InterpretationContext

__all__ = [
    "CognitiveMeaningPacket",
    "INITIAL_LOCALES",
    "InterpretationContext",
    "InterpretationResult",
    "NeuroLingua",
    "PIPELINE_STAGES",
    "RenderedOutput",
    "create_neuro_lingua",
    "interpret",
    "realize",
]
