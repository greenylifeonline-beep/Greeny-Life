"""D2 Authoritative Run Supervisor.

The only component allowed to emit GATES_SATISFIED / work-gate state.
Printed PASS is never success.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

from .certification import (
    AssertionRegistry,
    AtomicCertificationRunner,
    EvidenceLedger,
    ExitCodePropagator,
    FalsePassDetector,
)
from .config import FailClosed, contains_forbidden_success, sha256_obj, utc_now
from .cursor_probe import governed_invoke, probe_clients
from .failure_capture import FailureCaptureKernel
from .idle_recert import IdleRecertification
from .meta_learning import MetaLearning
from .process_kernel import EncodingSafeProcessKernel, KernelObservation, encoding_safe_run
from .repair_memory import RepairMemory, RepairPlanner
from .resource_governor import ResourceGovernor
from .root_cause import classify_failure, graph_from_observation
from .shadow_lab import ShadowRepairLab
from .work_gate import READY, WorkGate

GateFn = Callable[[AssertionRegistry], Any]


class AuthoritativeRunSupervisor:
    def __init__(
        self,
        ledger: EvidenceLedger,
        gate: WorkGate,
        *,
        causal=None,
        repair_memory: RepairMemory | None = None,
        planner: RepairPlanner | None = None,
        governor: ResourceGovernor | None = None,
        meta: MetaLearning | None = None,
    ) -> None:
        self.ledger = ledger
        self.gate = gate
        self.kernel = EncodingSafeProcessKernel()
        self.capture = FailureCaptureKernel(ledger)
        self.cert = AtomicCertificationRunner(ledger)
        self.detector = FalsePassDetector()
        self.propagator = ExitCodePropagator()
        self.causal = causal
        self.repair_memory = repair_memory
        self.planner = planner
        self.lab = ShadowRepairLab()
        self.governor = governor or ResourceGovernor()
        self.idle = IdleRecertification(self.governor)
        self.meta = meta or MetaLearning()
        self.gate.close(["SUPERVISOR_CONSTRUCTED"], {"supervisor": True})

    def run_child(
        self,
        argv: Sequence[str],
        *,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
        strict_utf8: bool = False,
    ) -> KernelObservation:
        try:
            obs = self.kernel.run(list(argv), cwd=cwd, timeout=timeout, strict_utf8=strict_utf8)
        except FailClosed as exc:
            self.capture.capture(name="run_child", error=str(exc))
            raise
        try:
            self.detector.judge_child(obs.stdout, obs.stderr, obs.returncode)
        except FailClosed as exc:
            self.capture.capture(name="run_child", error=str(exc), obs=obs)
            raise
        return obs

    def certify(self, name: str, fn: GateFn, run_id: str) -> dict[str, Any]:
        result = self.cert.certify(name, fn, run_id)
        if result.get("ok") and result.get("overall_status") == "GATES_SATISFIED":
            return result
        self.gate.close(["CERTIFICATION_FAILED:" + name], {"ok": False})
        if contains_forbidden_success(str(result.get("error") or "")) and result.get("ok"):
            raise FailClosed("SYSTEM_INTEGRITY_FAILURE")
        return result

    def evaluate_boot(self, components: dict[str, Any]) -> dict[str, Any]:
        required_ready = {
            "process_kernel": bool(components.get("process_kernel")),
            "run_supervisor": bool(components.get("run_supervisor")),
            "failure_capture": bool(components.get("failure_capture")),
            "anti_false_pass": bool(components.get("anti_false_pass")),
            "work_gate": bool(components.get("work_gate")),
            "experience_capture": bool(components.get("experience_capture")),
            "shadow_lab": bool(components.get("shadow_lab")),
            "main_cortex": bool(components.get("main_cortex")),
            "shared_state": bool(components.get("shared_state")),
            "memory": bool(components.get("memory")),
            "permission_system": bool(components.get("permission_system")),
        }
        missing = [k for k, v in required_ready.items() if not v]
        probe = probe_clients()
        body = {
            "created_at": utc_now(),
            "components": {**components, "cursor_probe": probe},
            "missing": missing,
            "work_gate_print_override_forbidden": True,
        }
        if "WORK_GATE=OPEN" in str(components):
            raise FailClosed("SYSTEM_INTEGRITY_FAILURE")
        if missing:
            reasons = [f"MISSING:{k}" for k in missing]
            only_cortex = missing == ["main_cortex"]
            if only_cortex:
                gate = self.gate.set_degraded(reasons, body["components"])
                body["gate"] = gate
                body["overall_status"] = "DEGRADED_DIAGNOSTIC_ACTIVE"
                body["exit_code"] = 0
                return body
            gate = self.gate.close(reasons, body["components"])
            body["gate"] = gate
            body["overall_status"] = "FAILED"
            body["exit_code"] = 1
            return body
        gate = self.gate.open_ready(body["components"])
        body["gate"] = gate
        body["overall_status"] = "READY_FOR_REAL_PROJECT_WORK"
        body["exit_code"] = 0
        body["sha256"] = sha256_obj(body)
        return body

    def invoke_cursor(self, *args: Any, **kwargs: Any) -> Any:
        intent = str(args[0] if args else kwargs.get("intent") or "repair")
        mutating = bool(kwargs.get("mutating", intent != "observe"))
        if mutating or self.gate.read().get("state") != READY:
            governed_invoke(*args, **kwargs)
        raise FailClosed("CURSOR_MUTATING_INVOCATION_NOT_AUTHORIZED")


def encoding_safe_child(argv: Sequence[str], **kwargs: Any) -> KernelObservation:
    return encoding_safe_run(list(argv), **kwargs)
