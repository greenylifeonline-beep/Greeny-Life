"""Parallel wave runtime facade."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter import NativeCortexBridge
from .auditor import RealityAuditor
from .context import ContextCompiler
from .cortex import CortexRegistry
from .distillation import DistillationFactory
from .experience import ExperienceStore
from .governance import Governance
from .identity import FailClosed, assert_not_protected_live_writer, repo_root_from
from .ingest import ObservationIngest
from .knowledge import KnowledgeDebtEngine, KnowledgeLibrary
from .live_learning import LiveStudentEngine
from .maintenance import Maintenance
from .mastery import MasteryEngine
from .memory import MemorySPI
from .retirement import RetirementEngine
from .rkg import CognitiveGraph
from .scheduler import ComputeScheduler
from .semantic_validation import SemanticVerifier
from .skills import SkillCompiler
from .store import Store
from .transfer_graph import TransferGraph


class ParallelRuntime:
    def __init__(self, root: str | Path, repo_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else repo_root_from()
        self.root = Path(root)
        assert_not_protected_live_writer(self.root, self.repo_root)
        if "RAIOS/V9" in str(self.root).replace("\\", "/"):
            raise FailClosed("RAIOS_V9_MUTATION_REJECTED")
        if "_raios-a17-native-cortex" in str(self.root).replace("\\", "/"):
            raise FailClosed("PROTECTED_LIVE_WRITER:_raios-a17-native-cortex")
        self.store = Store(self.root, repo_root=self.repo_root)
        self.governance = Governance(self.store)
        self.rkg = CognitiveGraph(self.store)
        self.ingest = ObservationIngest(self.store)
        self.live = LiveStudentEngine(self.store)
        self.verifier = SemanticVerifier(self.store)
        self.mastery = MasteryEngine(self.store)
        self.retirement = RetirementEngine(self.store, self.mastery, self.governance)
        self.graph = TransferGraph(self.store, self.mastery, self.retirement)
        self.experience = ExperienceStore(self.store, self.rkg)
        self.knowledge = KnowledgeLibrary(self.store, self.rkg)
        self.knowledge_debt = KnowledgeDebtEngine(self.store)
        self.skills = SkillCompiler(self.store, self.governance)
        self.factory = DistillationFactory(self.store, self.governance)
        self.scheduler = ComputeScheduler(self.store)
        self.maintenance = Maintenance(self.store, self.governance)
        self.cortex = CortexRegistry(self.store, self.governance)
        self.compiler = ContextCompiler()
        self.memory = MemorySPI(self.store)
        self.bridge = NativeCortexBridge(self.repo_root)
        self.auditor = RealityAuditor(self)

    def close(self) -> None:
        self.store.close()

    def shared_state(self) -> dict[str, Any]:
        ident = self.store.identity()
        return {
            "identity": ident["organism_id"],
            "shared": [
                "Identity", "Memory", "Knowledge", "RKG", "Experience",
                "Skills", "Policies", "Learning", "Competency", "Evidence",
            ],
            "per_agent_canonical_memory": False,
            "cortex_is_identity": False,
        }
