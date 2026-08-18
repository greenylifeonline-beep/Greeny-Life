"""Wave runtime facade — isolated store, never writes to live A17.4 or V9 canonical paths."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import (
    A174HarvestAdapter,
    CognitiveExchangeAdapter,
    LearningFabricAdapter,
    ModelEscalationAdapter,
    V9ContinuityAdapter,
)
from .assimilation import Normalizer
from .context import ContextCompiler
from .cortex import CortexRegistry
from .differential import DifferentialEngine
from .experience import ExperiencePlane
from .governance import Governance
from .identity import FailClosed, assert_not_protected_live_writer, repo_root_from
from .knowledge import KnowledgeDebtEngine, KnowledgeLibrary
from .loop import CognitiveLoop, ToolAuthority
from .mastery import MasteryEngine
from .memory import MemorySPI
from .retirement import RetirementEngine
from .rkg import CognitiveGraph
from .skills import SkillSPI
from .store import Store
from .training import TrainingCorpus


class WaveRuntime:
    def __init__(self, root: str | Path, repo_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else repo_root_from()
        self.root = Path(root)
        assert_not_protected_live_writer(self.root, self.repo_root)
        if "RAIOS/V9" in str(self.root).replace("\\", "/"):
            raise FailClosed("RAIOS_V9_MUTATION_REJECTED")
        self.store = Store(self.root, repo_root=self.repo_root)
        self.governance = Governance(self.store)
        self.rkg = CognitiveGraph(self.store)
        self.normalizer = Normalizer(self.store)
        self.differential = DifferentialEngine(self.store)
        self.mastery = MasteryEngine(self.store)
        self.retirement = RetirementEngine(self.store, self.mastery, self.governance)
        self.training = TrainingCorpus(self.store)
        self.cortex = CortexRegistry(self.store)
        self.compiler = ContextCompiler()
        self.experience = ExperiencePlane(self.store, self.rkg)
        self.knowledge = KnowledgeLibrary(self.store, self.rkg)
        self.knowledge_debt = KnowledgeDebtEngine(self.store)
        self.memory = MemorySPI(self.store)
        self.skills = SkillSPI(self.store)
        self.tools = ToolAuthority(self.store, self.governance)
        self.loop = CognitiveLoop(
            self.store,
            compiler=self.compiler,
            cortex=self.cortex,
            tools=self.tools,
            experience=self.experience,
            mastery=self.mastery,
            differential=self.differential,
            knowledge=self.knowledge,
        )
        self.a174 = A174HarvestAdapter(self.repo_root)
        self.fabric = LearningFabricAdapter(self.repo_root)
        self.exchange = CognitiveExchangeAdapter(self.repo_root)
        self.v9 = V9ContinuityAdapter(self.repo_root)
        self.escalation = ModelEscalationAdapter(self.repo_root)

    def close(self) -> None:
        self.store.close()

    def reuse_status(self) -> dict[str, Any]:
        return {
            "learning_fabric": self.fabric.status(),
            "cognitive_exchange": self.exchange.status(),
            "v9_identity": {"path": str(self.v9.identity_path), "read_only": True},
            "model_escalation": self.escalation.status(),
            "a17_4": self.a174.status(),
        }
