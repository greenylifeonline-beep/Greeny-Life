"""A17.10 Unified cognitive loop skeleton.

MODEL_OUTPUT != EXECUTION_AUTHORITY. Tools execute only through RAIOS
authority. Cortex text cannot mutate filesystem, database, or canonical state.
"""
from __future__ import annotations

from typing import Any, Callable

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import EventType, LoopStage


FORBIDDEN_TOOL_TARGETS = ("filesystem", "database", "canonical", "sqlite", "identity")


class ToolAuthority:
    def __init__(self, store: Any, governance: Any) -> None:
        self.store = store
        self.governance = governance

    def execute(self, plan: dict[str, Any], *, authorized: bool) -> dict[str, Any]:
        if not authorized:
            raise FailClosed("MODEL_OUTPUT_IS_NOT_EXECUTION_AUTHORITY")
        tool = str(plan.get("tool") or "")
        target = str(plan.get("target") or "")
        if any(token in target.lower() for token in FORBIDDEN_TOOL_TARGETS) and plan.get("mutate"):
            self.governance.reject("APPLY_CORTEX_TEXT", plan)
        return {
            "tool": tool,
            "target": target,
            "executed": True,
            "authority": "RAIOS",
            "result": plan.get("simulated_result", "OK"),
        }


class CognitiveLoop:
    STAGES = list(LoopStage)

    def __init__(
        self,
        store: Any,
        *,
        compiler: Any,
        cortex: Any,
        tools: ToolAuthority,
        experience: Any,
        mastery: Any,
        differential: Any,
        knowledge: Any,
    ) -> None:
        self.store = store
        self.compiler = compiler
        self.cortex = cortex
        self.tools = tools
        self.experience = experience
        self.mastery = mastery
        self.differential = differential
        self.knowledge = knowledge

    def run(self, task: dict[str, Any], *, authorize_tools: bool = False, hooks: dict[str, Callable] | None = None) -> dict[str, Any]:
        run_id = deterministic_id("loop", str(task.get("task_id") or task.get("id") or "task"), utc_now())
        stages: list[dict[str, Any]] = []
        context = {
            "task": task,
            "observations": task.get("observations") or [],
            "memory": task.get("memory") or [],
            "rkg": task.get("rkg") or [],
            "skills": task.get("skills") or [],
            "experience": task.get("experience") or [],
            "failures": task.get("failures") or [],
            "policies": task.get("policies") or [],
            "evidence": task.get("evidence") or [],
            "learning_state": task.get("learning_state") or [],
        }
        proposal = None
        execution = None
        compiled = None
        for stage in self.STAGES:
            record = {"stage": stage.value, "status": "OK", "at": utc_now()}
            if hooks and stage.value in hooks:
                record["hook"] = hooks[stage.value](context)
            if stage is LoopStage.CONTEXT_COMPILER:
                compiled = self.compiler.compile(
                    task=task,
                    observations=context["observations"],
                    memory=context["memory"],
                    rkg=context["rkg"],
                    skills=context["skills"],
                    experience=context["experience"],
                    failures=context["failures"],
                    policies=context["policies"],
                    evidence=context["evidence"],
                    learning_state=context["learning_state"],
                    budget_tokens=int(task.get("budget_tokens") or 1024),
                )
                record["manifest_id"] = compiled["manifest_id"]
                context["compiled"] = compiled
            elif stage is LoopStage.MAIN_CORTEX:
                prompt = canonical_json({"task": task.get("goal") or task, "manifest": compiled})
                proposal = self.cortex.active.infer(prompt)
                record["proposal_id"] = proposal.proposal_id
                record["execution_authority"] = False
                context["proposal"] = proposal
            elif stage is LoopStage.TOOL_AUTHORITY:
                plan = {"tool": "noop", "target": "workspace-sandbox", "mutate": False}
                if proposal and proposal.tool_plan:
                    plan = dict(proposal.tool_plan[0])
                    plan.setdefault("mutate", False)
                try:
                    execution = self.tools.execute(plan, authorized=authorize_tools)
                    record["execution"] = execution
                except FailClosed as exc:
                    record["status"] = "BLOCKED"
                    record["reason"] = str(exc)
                    execution = {"executed": False, "reason": str(exc)}
            elif stage is LoopStage.EXECUTION:
                record["model_output_is_execution_authority"] = False
                record["executed"] = bool(execution and execution.get("executed"))
            elif stage is LoopStage.VERIFICATION:
                record["verified"] = bool(task.get("verification_pass"))
            elif stage is LoopStage.EXPERIENCE_RECORD:
                exp = self.experience.record_from_loop(run_id, task, proposal, execution, compiled)
                record["experience_id"] = exp["experience_id"]
                context["experience_id"] = exp["experience_id"]
            elif stage is LoopStage.LEARNING_OBLIGATION:
                record["obligation"] = "ATTENDANCE_REQUIRED"
                record["auto_pay"] = False
            elif stage is LoopStage.ASSIMILATION:
                record["competency_update"] = "PROPOSED"
                record["canonical"] = False
            self.store.append_event(EventType.LOOP_STAGE, run_id, record)
            stages.append(record)
        payload = {
            "run_id": run_id,
            "task_id": task.get("task_id") or task.get("id"),
            "stages": stages,
            "proposal_id": getattr(proposal, "proposal_id", None),
            "direct_canonical_mutation": False,
            "model_output_is_execution_authority": False,
        }
        self.store.conn.execute(
            "INSERT INTO loop_runs(run_id, task_id, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (run_id, str(payload["task_id"]), canonical_json(payload), utc_now()),
        )
        return payload
