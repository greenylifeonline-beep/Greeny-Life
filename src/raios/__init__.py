"""RAIOS V9 cognitive substrate for Greeny-Life EOS.

This package does **not** replace ``GreenyLifeBrain``. The host repository is
the GREENY LIFE Digital Operating System (GL-DOS). RAIOS V9 primitives
(Cognitive WAL, knowledge states, capability contracts) were specified by
NL-0 but were not present as Python modules; they are introduced here as a
language-layer substrate that NeuroLingua integrates with.

Public principle: **Model is replaceable. Meaning is canonical.**
"""

from .knowledge_state import KnowledgeState
from .risk import RiskLevel

__all__ = ["KnowledgeState", "RiskLevel", "__version__"]
__version__ = "9.0.0-nl0"
