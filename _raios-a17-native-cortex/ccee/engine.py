"""CCEE runtime façade. Shared state is explicit. Mutation is ledger/WAL only."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .arena import Arena
from .benchmark_factory import BenchmarkFactory
from .causal_learning import CausalLearning
from .checkpoint import Checkpoint
from .config import ORGANISM_ID, assert_not_v9, repo_root_from
from .conscious import ConsciousBrain
from .contradiction_engine import ContradictionEngine
from .curiosity import CuriosityEngine
from .curriculum import Curriculum
from .embeddings import LexicalMemory, detect_local_embedding_model
from .event_bus import EventBus
from .experience_metabolism import ExperienceMetabolism
from .failure_imagination import FailureImagination
from .forgetting import Forgetting
from .knowledge import KnowledgeMetabolism
from .learning_acceleration import LearningAcceleration
from .ledger import Ledger
from .meta_learning import MetaLearning
from .metrics import Metrics
from .ollama_runtime import OllamaRuntimeManager
from .replay import ReplayEngine
from .resource_governor import ResourceGovernor
from .retention import RetentionEngine
from .scheduler import Scheduler
from .skill_compiler import SkillCompiler
from .structured_inference import StructuredInference
from .subconscious import SubconsciousBrain
from .teacher_mining import TeacherMining
from .transfer import TransferEngine
from .wal import CognitiveWAL
from .workers import WorkerPool
from .certification import AtomicCertificationRunner, EvidenceLedger


class CCEE:
    def __init__(self, root: str | Path, repo_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else repo_root_from()
        self.root = Path(root)
        assert_not_v9(self.root, self.repo_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.wal = CognitiveWAL(self.root / "wal", repo_root=self.repo_root)
        self.ledger = Ledger(self.root / "ledger", repo_root=self.repo_root)
        self.bus = EventBus(self.wal)
        self.governor = ResourceGovernor()
        self.curiosity = CuriosityEngine(self.ledger)
        self.curriculum = Curriculum(self.ledger)
        self.conscious = ConsciousBrain(self.bus, self.governor)
        self.subconscious = SubconsciousBrain(self.wal, self.bus, self.curiosity, self.governor)
        self.metabolism = ExperienceMetabolism(self.ledger, self.bus)
        self.replay = ReplayEngine()
        self.imagination = FailureImagination(self.bus)
        self.causal = CausalLearning(self.bus)
        self.contradiction = ContradictionEngine(self.ledger, self.bus)
        self.skills = SkillCompiler(self.ledger, self.bus)
        self.teachers = TeacherMining(self.ledger, self.bus, repo_root=self.repo_root)
        self.transfer = TransferEngine(self.bus)
        self.retention = RetentionEngine(self.bus)
        self.forgetting = Forgetting(self.ledger, self.bus)
        self.meta = MetaLearning()
        self.benchmarks = BenchmarkFactory(self.bus, self.transfer)
        self.arena = Arena()
        self.accel = LearningAcceleration(self.ledger)
        self.metrics = Metrics(self.accel)
        self.scheduler = Scheduler(self.governor, self.subconscious, self.curriculum)
        self.ollama = OllamaRuntimeManager(self.bus)
        self.structured = StructuredInference()
        self.memory = LexicalMemory()
        self.embedding_status = detect_local_embedding_model()
        self.knowledge = KnowledgeMetabolism(self.ledger, self.bus)
        self.checkpoint = Checkpoint(self.wal, self.ledger)
        self.workers = WorkerPool({})
        evidence_root = Path(self.root) / "evidence"
        self.evidence = EvidenceLedger(evidence_root, repo_root=self.repo_root)
        self.cert = AtomicCertificationRunner(self.evidence)

    def close(self) -> None:
        self.workers.shutdown()
        self.wal.close()
        self.ledger.close()

    def identity(self) -> dict[str, Any]:
        return {
            "organism_id": ORGANISM_ID,
            "cortex_is_identity": False,
            "shared_state": True,
            "uncontrolled_mutation": False,
        }
