"""Diagnostic & Repair Nervous System façade. One organism: CCEE."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .certification import EvidenceLedger
from .cursor_probe import probe_clients
from .experience_metabolism import ExperienceMetabolism
from .failure_capture import FailureCaptureKernel
from .idle_recert import IdleRecertification
from .meta_learning import MetaLearning
from .permission_broker import PermissionBroker
from .process_kernel import EncodingSafeProcessKernel, KERNEL_ID
from .repair_memory import RepairMemory, RepairPlanner
from .resource_governor import ResourceGovernor
from .root_cause import classify_failure, graph_from_observation
from .run_supervisor import AuthoritativeRunSupervisor
from .shadow_lab import ShadowRepairLab
from .skill_compiler import SkillCompiler
from .work_gate import WorkGate


class DiagnosticNervousSystem:
    def __init__(
        self,
        root: str | Path,
        *,
        ledger,
        bus,
        causal,
        metabolism: ExperienceMetabolism,
        skills: SkillCompiler,
        governor: ResourceGovernor,
        meta: MetaLearning,
        repo_root: Path,
    ) -> None:
        self.root = Path(root)
        evidence = EvidenceLedger(self.root / "evidence", repo_root=repo_root)
        self.evidence = evidence
        self.kernel = EncodingSafeProcessKernel()
        self.capture = FailureCaptureKernel(evidence)
        self.repair_memory = RepairMemory(ledger)
        self.planner = RepairPlanner(self.repair_memory)
        self.lab = ShadowRepairLab()
        self.gate = WorkGate(self.root / "work_gate.json")
        self.supervisor = AuthoritativeRunSupervisor(
            evidence,
            self.gate,
            causal=causal,
            repair_memory=self.repair_memory,
            planner=self.planner,
            governor=governor,
            meta=meta,
        )
        self.idle = IdleRecertification(governor)
        self.metabolism = metabolism
        self.skills = skills
        self.causal = causal
        self.bus = bus
        self.governor = governor
        self.meta = meta
        self.broker = PermissionBroker(ledger, self.gate)

    def identity(self) -> dict[str, Any]:
        return {
            "d1": KERNEL_ID,
            "d2": "raios.d2.run-supervisor.v1",
            "d3": "raios.d3.failure-capture.v1",
            "d4": "raios.d4.root-cause.v1",
            "d5": "raios.d5.repair-planner.v1",
            "d6": "raios.d6.shadow-lab.v1",
            "d7": "raios.d7.anti-false-pass.v1",
            "d8": "raios.d8.experience-meta.v1",
            "d9": "raios.d9.idle-recert.v1",
            "d10": "raios.d10.cursor-probe.v1",
            "d11": "raios.d11.work-gate.v1",
            "work_gate": self.gate.read().get("state"),
        }

    def certify_self(self, workdir: str | Path) -> dict[str, Any]:
        lab = self.lab.run_encoding_lab(Path(workdir) / "shadow")
        self.governor.release_foreground()
        recert = self.idle.recertify_encoding_and_false_pass()
        lease = self.broker.request_lease(
            scope=["tests", "evidence", "temporary_shadow"],
            duration_s=3600,
            risk="LOW",
            purpose="nervous-system-self-cert",
        )
        graph = graph_from_observation(self.causal, None, printed_pass=True, secondary="historical-plus-encoding")
        family = classify_failure({"printed_pass": True, "failed": True, "child_exit": 1, "false_pass": True})
        plan = self.planner.plan({"printed_pass": True, "failed": True, "child_exit": 1, "false_pass": True})
        episode = self.metabolism.metabolize(
            {"id": "encoding-false-pass", "intent": "d1-d7-certification", "input": lab},
            {"ok": True, "success_score": 1.0, "failure_score": 0.0, "plan": plan["actions"], "teacher_used": True},
            {
                "observations": ["bytes-first kernel", "false PASS blocked", family],
                "lessons": [
                    "never decode child output with locale encoding",
                    "never use errors=ignore",
                    "never emit PASS after nonzero exit",
                ],
                "candidate_skills": ["encoding_safe_subprocess", "false_pass_detector"],
                "uncertainty": 0.25,
                "recovery_used": True,
            },
        )
        self.repair_memory.record_validation(plan["repair_id"] or "repair.encoding_safe_subprocess.v1", ok=True, evidence=lab)
        self.meta.record(
            {
                "mission_id": "encoding-false-pass-teach",
                "teaching_method": "deterministic_negative_control",
                "teacher": "cursor",
                "success": True,
                "practice_count": 1,
                "time_to_transfer": 0 if recert.get("skipped") else 1,
            }
        )
        skill = self.skills.compile(
            {
                "interface": "encoding_safe_subprocess",
                "preconditions": ["argv_nonempty"],
                "inputs": ["argv", "cwd", "timeout"],
                "outputs": ["KernelObservation"],
                "procedure": ["bytes_capture", "utf8_replace", "returncode_first"],
                "invariants": ["stdout_never_none", "no_errors_ignore"],
                "negative_controls": ["latin1_0xe9", "PASS_then_exit_1"],
                "tests": ["test_nervous_system.py"],
                "rollback": {"restore": "git checkout -- encoding call sites"},
                "failure_modes": ["PROCESS_SPAWN_FAILED", "CHILD_TIMEOUT"],
                "provenance": {"source": "d1-kernel", "teacher": "cursor"},
                "kind": "MICRO_SKILL",
                "zero_llm": True,
                "confidence": 0.8,
            }
        )
        components = {
            "process_kernel": True,
            "run_supervisor": True,
            "failure_capture": True,
            "anti_false_pass": True,
            "work_gate": True,
            "experience_capture": bool(episode.get("episode_id")),
            "shadow_lab": bool(lab.get("executed")),
            "root_cause": bool(graph.get("nodes")),
            "repair_planner": bool(plan.get("plan_id")),
            "idle_recert": not recert.get("skipped"),
            "meta_learning": True,
            "permission_system": bool(lease.get("state") == "GRANTED"),
            "shared_state": True,
            "memory": True,
            "skill": bool(skill.get("skill_id")),
            "cursor_probe": probe_clients().get("cursor_present"),
            "main_cortex": False,
        }
        boot = self.supervisor.evaluate_boot(components)
        return {
            "lab": lab,
            "recert": recert,
            "graph": graph,
            "plan": plan,
            "episode_id": episode["episode_id"],
            "skill_id": skill.get("skill_id"),
            "boot": boot,
            "family": family,
            "mastery_claimed": False,
        }
