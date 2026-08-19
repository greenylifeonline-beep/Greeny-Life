"""Live Cursor↔RAIOS cognitive training loop.

Reuses CognitiveTurn, CortexResponse, WAL, repair memory, D1 kernel, D4
classifier, and the permission broker. Not a parallel brain.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import FailClosed, canonical_json, deterministic_id, native_root, repo_root_from, sha256_obj, utc_now
from .process_kernel import encoding_safe_run
from .repair_memory import KERNEL_REPAIR_ID
from .root_cause import classify_failure
from .schemas import CognitiveTurn, CriticScore, QueueName
from .work_gate import WorkGate

MAX_ATTEMPTS = 3
SKIP_HINTS = ("/archive/", "\\.architecture-backups\\", "/node_modules/", "/.git/")
TAUGHT_MARKERS = (
    "text=true",
    "errors=ignore",
    "encoding class",
    "over-classified subprocess.check_output",
    "do not mutate raios/v9",
)

UNTAUGHT_STRATEGIES = {
    1: "naive_repo_rg",
    2: "exclude_archive",
    3: "expand_popen_check_output",
}
TAUGHT_STRATEGIES = {
    1: "expand_popen_check_output",
    2: "exclude_v9_brain",
    3: "certify_harness_only",
}
FALSE_PASS_STRATEGIES = {
    1: "naive_print_pass",
    2: "except_after_pass",
    3: "gates_complete_returncode",
}
GATEWAY_STRATEGIES = {
    1: "naive_repo_rg",
    2: "incident_evidence_probe",
    3: "gateway_shadow_integrity",
}
EXECUTOR_STRATEGIES = {
    1: "which_executors",
    2: "gh_copilot_help",
    3: "cursor_env_probe",
}


def _skip(path: str) -> bool:
    lowered = path.replace("\\", "/")
    return any(h.replace("\\", "/") in lowered for h in SKIP_HINTS)


def classify_hit(line: str) -> str:
    """Bucket a rg hit. Teacher-compiled from GL-ENC-002; not independent Qwen insight."""
    lowered = line.replace("\\", "/")
    if _skip(lowered):
        return "archive_skip"
    path = lowered.split(":", 1)[0]
    if "RAIOS/V9/" in lowered:
        return "v9_forbidden"
    if path == "brain.py" or path.endswith("/brain.py"):
        return "brain_quarantined"
    if "errors='strict'" in line or 'errors="strict"' in line:
        return "negative_control"
    if path.endswith("/process_kernel.py") or path.endswith("process_kernel.py"):
        return "comment"
    if path.endswith("/training_loop.py") or path.endswith("training_loop.py"):
        return "classifier_source"
    if "text=True" in line or "errors='ignore'" in line or 'errors="ignore"' in line:
        return "reconnectable_d1"
    return "needs_review"


def classify_hit_with_context(line: str) -> str:
    """Same-line bucket plus a short look-ahead for multi-line negative controls."""
    base = classify_hit(line)
    if base != "reconnectable_d1":
        return base
    parts = line.split(":", 2)
    if len(parts) < 2:
        return base
    path = Path(parts[0])
    try:
        lineno = int(parts[1])
    except ValueError:
        return base
    if not path.is_file():
        return base
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return base
    start = max(0, lineno - 1)
    window = "\n".join(rows[start : min(len(rows), start + 8)])
    if "errors='strict'" in window or 'errors="strict"' in window:
        return "negative_control"
    return base


def classify_fp_hit(line: str) -> str:
    lowered = line.replace("\\", "/")
    if _skip(lowered):
        return "archive_skip"
    path = lowered.split(":", 1)[0]
    if "RAIOS/V9/" in lowered:
        return "v9_forbidden"
    if path == "brain.py" or path.endswith("/brain.py"):
        return "brain_quarantined"
    if path.endswith("/certification.py") or path.endswith("test_false_pass.py") or path.endswith("/doctor.py"):
        return "detector_or_adversarial"
    if "WAVE_CERTIFICATION" in line or '"PASS" if' in line or "'PASS' if" in line:
        return "certify_claim_label"
    if "print('PASS')" in line or 'print("PASS")' in line:
        return "liar_print"
    if "gates_complete=completed.returncode" in line:
        return "returncode_as_gates"
    return "needs_review"


class LiveCognitiveLoop:
    def __init__(self, ccee: Any, repo_root: Path | None = None) -> None:
        self.ccee = ccee
        self.repo = Path(repo_root or ccee.repo_root or repo_root_from())
        self.queues: dict[str, list[str]] = defaultdict(list)
        self._commands: dict[str, list[str]] = defaultdict(list)
        self._attempts: dict[str, int] = defaultdict(int)
        self._restore()

    def persist_turn(self, turn: CognitiveTurn) -> dict[str, Any]:
        dumped = json.loads(turn.model_dump_json())
        dumped["created_at"] = utc_now()
        dumped["canonical"] = False
        kid = deterministic_id("turn", turn.task_id, str(turn.attempt), turn.actor, sha256_obj(dumped)[:8])
        dumped["turn_id"] = kid
        self.ccee.knowledge.ingest("observation", f"cognitive_turn:{kid}")
        self.ccee.ledger.put(
            "knowledge",
            "knowledge_id",
            kid,
            dumped,
            extra={"state": "DISCOVERED", "kind": "observation"},
        )
        event_type = "CURSOR_TURN" if turn.actor == "CURSOR" else "RAIOS_TURN"
        if turn.queue == "BLOCKED":
            event_type = "BLOCKED_TASK"
        self.ccee.bus.emit(event_type, turn.actor.lower(), dumped, confidence=turn.confidence)
        self._queue_set(turn.task_id, turn.queue)
        return dumped

    def _restore(self) -> None:
        latest: dict[str, dict[str, Any]] = {}
        for rec in self.ccee.ledger.list("knowledge"):
            if rec.get("schema_id") != "raios.cognitive-turn.v1":
                continue
            tid = str(rec.get("task_id") or "")
            if not tid:
                continue
            if rec.get("actor") == "RAIOS":
                self._attempts[tid] = max(self._attempts[tid], int(rec.get("attempt") or 0))
                for taken in rec.get("action_taken") or []:
                    argv = taken.get("argv")
                    if argv:
                        key = sha256_obj({"argv": argv})
                        if key not in self._commands[tid]:
                            self._commands[tid].append(key)
            prev = latest.get(tid)
            if prev is None or str(rec.get("created_at") or "") >= str(prev.get("created_at") or ""):
                latest[tid] = rec
        for tid, rec in latest.items():
            queue = rec.get("queue") or "READY"
            self.queues[queue] = [t for t in self.queues[queue] if t != tid]
            self.queues[queue].append(tid)

    def retrieved_lessons(self) -> list[str]:
        lessons: list[str] = []
        for rec in self.ccee.ledger.list("knowledge"):
            if rec.get("schema_id") != "raios.cognitive-turn.v1":
                continue
            for item in rec.get("lesson") or []:
                text = str(item)
                if text and text not in lessons:
                    lessons.append(text)
        return lessons

    def encoding_class_taught(self) -> bool:
        blob = " ".join(self.retrieved_lessons()).lower()
        return any(marker in blob for marker in TAUGHT_MARKERS)

    def _choose_strategy(self, attempt: int, override: str | None, task_id: str = "") -> str:
        if override:
            return override
        if str(task_id).startswith("GL-FP"):
            mapping = FALSE_PASS_STRATEGIES
        elif str(task_id).startswith("GL-GW"):
            mapping = GATEWAY_STRATEGIES
        elif str(task_id).startswith("GL-EX"):
            mapping = EXECUTOR_STRATEGIES
        else:
            mapping = TAUGHT_STRATEGIES if self.encoding_class_taught() else UNTAUGHT_STRATEGIES
        if attempt not in mapping:
            raise FailClosed(f"NO_STRATEGY_FOR_ATTEMPT:{attempt}")
        return mapping[attempt]

    def _queue_set(self, task_id: str, queue: QueueName) -> None:
        for name, items in self.queues.items():
            self.queues[name] = [t for t in items if t != task_id]
        self.queues[queue].append(task_id)
        self.ccee.bus.emit(
            "QUEUE_TRANSITION",
            "loop",
            {"task_id": task_id, "queue": queue, "at": utc_now(), "ns": time.time_ns()},
        )

    def queues_snapshot(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.queues.items()}

    def ask_raios(self, *, task_id: str, intent: str, strategy: str | None = None) -> dict[str, Any]:
        attempt = self._attempts[task_id] + 1
        if attempt > MAX_ATTEMPTS:
            return self.block(task_id, intent, "MAX_ATTEMPTS")
        lessons = self.retrieved_lessons()
        strategy = self._choose_strategy(attempt, strategy, task_id)
        argv = self._search_argv(strategy)
        argv_key = sha256_obj({"argv": argv})
        if argv_key in self._commands[task_id]:
            raise FailClosed("IDENTICAL_RETRY_FORBIDDEN")
        self._commands[task_id].append(argv_key)
        self._attempts[task_id] = attempt
        lease = self.ccee.nervous.broker.request_lease(
            scope=["repository reads", "structural search", "generated diagnostic evidence"],
            duration_s=1800,
            risk="LOW",
            purpose=f"{task_id}:{attempt}",
        )
        gw_probe: dict[str, Any] | None = None
        if strategy == "incident_evidence_probe":
            from .gateway_incident import execute_incident_probe

            gw_probe = execute_incident_probe(self.repo, causal=self.ccee.causal, ollama=self.ccee.ollama)
            lines = list((gw_probe.get("token_search") or {}).get("hits_preview") or [])
            class _Obs:
                stdout = "\n".join(lines)
                returncode = int((gw_probe.get("token_search") or {}).get("returncode") or 0)
                stdout_sha256 = str(gw_probe.get("evidence_sha256") or "")
                integrity = str((gw_probe.get("token_search") or {}).get("integrity") or "OK")
                decode_replaced = False

            obs = _Obs()
        elif strategy == "gateway_shadow_integrity":
            from .shadow_lab import ShadowRepairLab

            lab_dir = Path(self.ccee.root) / "shadow" / task_id / f"attempt-{attempt}"
            gw_probe = ShadowRepairLab().run_gateway_false_pass_session(lab_dir)
            gw_probe.setdefault(
                "action_taken",
                [{"tool": "shadow_lab.gateway_false_pass", "executed": True, "mutating": False, "workdir": str(lab_dir)}],
            )
            gw_probe.setdefault("d4_family", "FALSE_PASS")
            gw_probe.setdefault("student_claims", {"lab": gw_probe.get("lab"), "repair_success": gw_probe.get("repair_success")})
            lines = [canonical_json({"lab": gw_probe.get("lab"), "repair_success": gw_probe.get("repair_success")})]
            class _Obs2:
                stdout = "\n".join(lines)
                returncode = 0 if gw_probe.get("repair_success") else 1
                stdout_sha256 = str(gw_probe.get("sha256") or "")
                integrity = "OK"
                decode_replaced = False

            obs = _Obs2()
        else:
            obs = encoding_safe_run(argv, cwd=self.repo, timeout=45.0)
            lines = [ln for ln in obs.stdout.splitlines() if ln.strip()]
        if strategy != "naive_repo_rg":
            lines = [ln for ln in lines if not _skip(ln)]
        buckets: dict[str, list[str]] = defaultdict(list)
        fp_task = task_id.startswith("GL-FP")
        gw_task = task_id.startswith("GL-GW")
        ex_task = task_id.startswith("GL-EX")
        if ex_task:
            buckets["executor_discovery"] = lines
            reconnectable = []
            actionable = lines
        elif gw_task:
            buckets["incident_hits"] = lines
            reconnectable = []
            actionable = lines
        else:
            for line in lines:
                buckets[(classify_fp_hit if fp_task else classify_hit_with_context)(line)].append(line)
            reconnectable = buckets.get("reconnectable_d1") or []
            actionable = reconnectable or buckets.get("returncode_as_gates") or buckets.get("liar_print") or []
        family = classify_failure(
            {
                "integrity": obs.integrity,
                "decode_replaced": obs.decode_replaced,
                "child_exit": obs.returncode,
                "printed_pass": bool(gw_task),
                "failed": obs.returncode not in {0, 1} or bool(gw_task),
                "http": 500 if gw_task else None,
            }
        )
        memory = self.ccee.nervous.repair_memory.get(KERNEL_REPAIR_ID)
        if gw_task:
            d4_family = (gw_probe or {}).get("d4_family") or family
            hypothesis = [
                {"family": d4_family, "repair_id": "repair.anti_false_pass.v1" if d4_family == "FALSE_PASS" else None},
                {"claim": "d4_family_from_incident_case", "value": d4_family},
                {"live_bypasses_detector": (gw_probe or {}).get("live_status_bypasses_pass_detector")},
                {"retrieved_lessons": lessons[:8]},
            ]
            plan = [
                "read HISTORICAL-GL-GW-001.json",
                "search HEALTH_CHECK|/v1/chat|GATEWAY_LIVE|QWEN_CHAT",
                "probe ollama inventory; do not invent chat PASS",
                "classify primary integrity vs runtime HTTP 500",
                "shadow-lab: health 200 + chat 500 + liar LIVE must fail closed",
            ]
            requested_tool = "d4.diagnose_incident"
        elif fp_task:
            hypothesis = [
                {"family": "FALSE_PASS", "repair_id": "repair.anti_false_pass.v1"},
                {"claim": "printed success tokens are never process authority"},
                {"retrieved_lessons": lessons[:8]},
            ]
            plan = [
                "search print('PASS') and SUCCESS tokens with D1 rg",
                "search swallowed exceptions after success prints",
                "search gates_complete=returncode and exit_code or 1",
                "judge_child must reject bare PASS exit 0 and PASS after nonzero",
                "do not mutate RAIOS/V9 or brain.py",
            ]
            requested_tool = "d7.judge_child"
        elif ex_task:
            hypothesis = [
                {"family": "EXECUTOR_DISCOVERY", "repair_id": None},
                {"claim": "client presence is not invocation authority"},
                {"retrieved_lessons": lessons[:8]},
            ]
            plan = [
                "discover cursor/gh/copilot binaries via D1",
                "probe gh copilot --help without credentials",
                "dispatch observe-only envelope under LOW lease",
                "mutating invoke remains fail-closed until D11 READY + human",
            ]
            requested_tool = "d10.governed_executor_bridge"
        else:
            hypothesis = [
                {"family": family or "UNICODE_DECODE", "repair_id": KERNEL_REPAIR_ID if memory else None},
                {"claim": "remaining locale-decoded subprocess callers are the same D1 class"},
                {"retrieved_lessons": lessons[:8]},
            ]
            plan = [
                "retrieve prior teacher lessons before choosing search strategy",
                "search subprocess/text=True callers with D1 rg",
                "classify v9_forbidden vs brain_quarantined vs negative_control vs reconnectable",
                "reconnect remaining reconnectable_d1 callers to encoding_safe_run",
                "negative control: latin1 0xe9 must not raise; PASS+exit1 must fail-closed",
            ]
            requested_tool = "d1.encoding_safe_run"
        turn = CognitiveTurn(
            task_id=task_id,
            attempt=attempt,
            actor="RAIOS",
            intent=intent,
            observations=[
                {
                    "strategy": strategy,
                    "hit_count": len(lines),
                    "returncode": obs.returncode,
                    "lessons_retrieved": len(lessons),
                    "encoding_class_taught": self.encoding_class_taught(),
                    "bucket_counts": {k: len(v) for k, v in sorted(buckets.items())},
                    "task_family": "gateway_false_pass" if gw_task else ("false_pass" if fp_task else ("executor" if ex_task else "encoding")),
                },
            ],
            evidence=[
                {"tool": "rg", "kernel": "d1", "stdout_sha256": obs.stdout_sha256, "integrity": obs.integrity},
                {"lease_id": lease["lease_id"]},
                *([{"incident": (gw_probe or {}).get("evidence_path"), "d4_family": (gw_probe or {}).get("d4_family")}] if gw_probe else []),
            ],
            hypothesis=hypothesis,
            plan=plan,
            action_requested=[
                {
                    "tool": requested_tool,
                    "targets": (actionable or reconnectable)[:20],
                    "mutating": True,
                    "requires": "HUMAN_OR_READY_GATE",
                    "do_not_mutate": ["RAIOS/V9", "brain.py"],
                },
            ],
            permission_scope=["repository reads", "structural search"],
            action_taken=(gw_probe or {}).get("action_taken")
            or [{"tool": "rg", "argv": argv, "executed": True, "mutating": False}],
            result={
                "ok": obs.returncode in {0, 1},
                "hits": lines[:60],
                "unsafe_preview": (actionable or reconnectable)[:20],
                "buckets": {k: v[:12] for k, v in buckets.items()},
                "strategy": strategy,
                "execution_authority": False,
                "teacher_authored_classifier": True,
                "gateway_diagnosis": gw_probe,
            },
            confidence=float((gw_probe or {}).get("confidence") or (0.55 if reconnectable else 0.25)),
            critic_score=0.0,
            failure_class=None if obs.returncode in {0, 1} else family,
            lesson=[],
            next_action=["cursor_critique", "reconnect_if_authorized"],
            queue="SHADOW_VALIDATION" if (actionable or reconnectable) else "READY",
            teacher_used=False,
        )
        persisted = self.persist_turn(turn)
        episode = self.ccee.metabolism.metabolize(
            {"id": task_id, "intent": intent, "input": {"strategy": strategy}},
            {"ok": bool(turn.result.get("ok")), "plan": turn.plan, "teacher_used": False, "success_score": 0.4},
            {"observations": turn.observations, "actions": turn.action_taken, "tool_calls": turn.action_taken, "uncertainty": 0.4},
        )
        persisted["episode_id"] = episode["episode_id"]
        if attempt >= MAX_ATTEMPTS and not (actionable or reconnectable):
            return self.block(task_id, intent, "NO_UNSAFE_HITS_AFTER_THREE")
        return persisted

    def _search_argv(self, strategy: str) -> list[str]:
        glob = ["--glob", "*.py"]
        repo = str(self.repo)
        if strategy == "naive_repo_rg":
            return ["rg", "-n", "--max-count", "200", *glob, r"subprocess\.(run|Popen|check_output|check_call)", repo]
        if strategy == "exclude_archive":
            return [
                "rg",
                "-n",
                "--max-count",
                "200",
                *glob,
                "-g",
                "!archive/**",
                "-g",
                "!.architecture-backups/**",
                r"subprocess\.(run|Popen|check_output|check_call)",
                repo,
            ]
        if strategy == "expand_popen_check_output":
            return [
                "rg",
                "-n",
                "--max-count",
                "200",
                *glob,
                "-g",
                "!archive/**",
                r"text\s*=\s*True|errors\s*=\s*['\"]ignore['\"]",
                repo,
            ]
        if strategy == "exclude_v9_brain":
            return [
                "rg",
                "-n",
                "--max-count",
                "200",
                *glob,
                "-g",
                "!archive/**",
                "-g",
                "!RAIOS/V9/**",
                "-g",
                "!brain.py",
                r"text\s*=\s*True|errors\s*=\s*['\"]ignore['\"]",
                repo,
            ]
        if strategy == "certify_harness_only":
            return [
                "rg",
                "-n",
                "--max-count",
                "200",
                "--glob",
                "*certify*.py",
                "-g",
                "!RAIOS/V9/**",
                "-g",
                "!archive/**",
                r"text\s*=\s*True",
                repo,
            ]
        if strategy == "naive_print_pass":
            return ["rg", "-n", "--max-count", "200", *glob, r"print\(['\"]PASS['\"]\)", repo]
        if strategy == "except_after_pass":
            return [
                "rg",
                "-n",
                "--max-count",
                "200",
                *glob,
                "-g",
                "!archive/**",
                r"print\(['\"]PASS['\"]\)|except Exception|except:",
                repo,
            ]
        if strategy == "gates_complete_returncode":
            return [
                "rg",
                "-n",
                "--max-count",
                "200",
                *glob,
                "-g",
                "!archive/**",
                r"gates_complete\s*=\s*completed\.returncode|exit_code\s+or\s+1",
                repo,
            ]
        if strategy == "which_executors":
            return [
                "bash",
                "-lc",
                "command -v cursor; command -v cursor-agent; command -v gh; command -v copilot; command -v github-copilot; true",
            ]
        if strategy == "gh_copilot_help":
            return ["bash", "-lc", "if command -v gh >/dev/null 2>&1; then gh copilot --help; else echo GH_MISSING; fi"]
        if strategy == "cursor_env_probe":
            return [
                "bash",
                "-lc",
                "printf 'CURSOR_AGENT=%s\\nCURSOR_CLOUD_AGENT=%s\\n' \"${CURSOR_AGENT-}\" \"${CURSOR_CLOUD_AGENT-}\"",
            ]
        if strategy == "incident_evidence_probe":
            return ["python3", "-m", "ccee.gateway_incident", "probe"]
        if strategy == "gateway_shadow_integrity":
            return ["python3", "-m", "ccee.shadow_lab", "gateway-false-pass"]
        raise FailClosed(f"UNKNOWN_STRATEGY:{strategy}")

    def critique(self, *, task_id: str, scores: dict[str, float], missed: list[str], supplied: list[str], notes: list[str]) -> dict[str, Any]:
        critic = CriticScore.model_validate(scores)
        turn = CognitiveTurn(
            task_id=task_id,
            attempt=self._attempts[task_id] or 1,
            actor="CURSOR",
            intent="teacher_critique",
            observations=notes,
            evidence=[{"missed": missed, "cursor_supplied": supplied}],
            hypothesis=[],
            plan=[],
            action_requested=[],
            permission_scope=["evaluation"],
            action_taken=[{"tool": "critic", "executed": True}],
            result={"scores": json.loads(critic.model_dump_json()), "mean": critic.mean()},
            confidence=min(1.0, critic.mean()),
            critic_score=critic.mean(),
            failure_class=None,
            lesson=notes,
            next_action=["adapt_strategy"] if critic.mean() < 0.6 else ["reconnect_or_promote_shadow"],
            queue="READY" if critic.mean() >= 0.5 else "READY",
            teacher_used=True,
        )
        dumped = self.persist_turn(turn)
        self.ccee.bus.emit("TEACHER_CRITIQUE", "cursor", dumped, confidence=turn.critic_score)
        self.ccee.meta.record(
            {
                "mission_id": f"critique:{task_id}:{turn.attempt}",
                "teaching_method": "cursor_critic",
                "teacher": "cursor",
                "success": critic.mean() >= 0.5,
                "practice_count": turn.attempt,
            }
        )
        return dumped

    def compile_d1_certify_skill(self, *, transfer_evidence: list[str]) -> dict[str, Any]:
        return self.ccee.skills.compile(
            {
                "interface": "d1_reconnect_certify_harness",
                "preconditions": ["encoding_class_taught", "caller_is_not_v9", "caller_is_not_brain"],
                "inputs": ["certify_harness_path"],
                "outputs": ["encoding_safe_run_child"],
                "procedure": [
                    "retrieve_prior_lessons",
                    "search_text_true_not_bare_check_output",
                    "classify_v9_brain_negative_control",
                    "replace_subprocess_run_text_true_with_encoding_safe_run",
                    "keep_returncode_before_status_text",
                ],
                "invariants": ["no_errors_ignore", "stdout_never_none", "v9_unchanged"],
                "negative_controls": ["latin1_0xe9", "PASS_then_exit_1", "errors=strict_left_intact"],
                "tests": ["test_training_loop.py", "test_nervous_system.py"],
                "rollback": {"restore": "git checkout -- certify harness"},
                "failure_modes": ["IDENTICAL_RETRY_FORBIDDEN", "V9_MUTATION_FORBIDDEN", "BRAIN_QUARANTINED"],
                "provenance": {"source": "gl-enc-002-teacher", "teacher": "cursor", "executor": "raios-search"},
                "kind": "MICRO_SKILL",
                "zero_llm": True,
                "confidence": 0.62,
                "transfer_evidence": transfer_evidence,
                "version": "0.2.0",
            }
        )

    def block(self, task_id: str, intent: str, reason: str) -> dict[str, Any]:
        turn = CognitiveTurn(
            task_id=task_id,
            attempt=self._attempts[task_id] or MAX_ATTEMPTS,
            actor="RAIOS",
            intent=intent,
            observations=[{"reason": reason, "commands": self._commands.get(task_id)}],
            evidence=[],
            hypothesis=[{"blocker": reason}],
            plan=["preserve_state", "schedule_revisit", "switch_independent_task"],
            action_requested=[{"unblock": reason}],
            permission_scope=[],
            action_taken=[],
            result={"blocked": True, "reason": reason},
            confidence=0.7,
            critic_score=0.0,
            failure_class=reason,
            lesson=["do_not_loop_after_three_distinct_failures"],
            next_action=["highest_value_independent_task"],
            queue="BLOCKED",
        )
        return self.persist_turn(turn)

    def continuity_review(self) -> dict[str, Any]:
        ollama = self.ccee.ollama.inventory()
        boot_gate = native_root(self.repo) / "ccee" / "var" / "boot" / "nervous" / "work_gate.json"
        if boot_gate.is_file():
            gate = json.loads(boot_gate.read_text(encoding="utf-8"))
        else:
            gate = WorkGate(self.ccee.nervous.gate.path).read()
        wal = self.ccee.wal.verify_chain()
        dirty = encoding_safe_run(["git", "status", "--porcelain"], cwd=self.repo)
        queues = self.queues_snapshot()
        blockers = []
        if not ollama.get("ok"):
            blockers.append("MAIN_CORTEX_UNREACHABLE")
        blockers.extend(f"QUEUE_BLOCKED:{tid}" for tid in queues.get("BLOCKED") or [])
        blockers.extend(f"WAITING_FOR_HUMAN:{tid}" for tid in queues.get("WAITING_FOR_HUMAN") or [])
        contradictions: list[dict[str, Any]] = []
        live_gate = self.ccee.nervous.gate.read()
        live_path = Path(self.ccee.nervous.gate.path).resolve()
        if gate.get("state") == "READY_FOR_REAL_PROJECT_WORK" and not ollama.get("main_cortex_present"):
            contradictions.append(
                {
                    "class": "CRITICAL",
                    "claim": "WORK_GATE_READY",
                    "reality": "MAIN_CORTEX_MISSING",
                    "evidence": ollama.get("reason"),
                }
            )
        if boot_gate.is_file() and live_path == boot_gate.resolve() and live_gate.get("state") != gate.get("state"):
            contradictions.append(
                {
                    "class": "CRITICAL",
                    "claim": f"boot_work_gate={gate.get('state')}",
                    "reality": f"live_work_gate={live_gate.get('state')}",
                    "evidence": "work_gate_file_mismatch",
                }
            )
        boot_receipt = native_root(self.repo) / "reports" / "RAIOS-BOOT-RECEIPT.json"
        if boot_receipt.is_file():
            prev = json.loads(boot_receipt.read_text(encoding="utf-8"))
            if prev.get("work_gate") == "READY_FOR_REAL_PROJECT_WORK" and gate.get("state") != "READY_FOR_REAL_PROJECT_WORK":
                contradictions.append(
                    {
                        "class": "CRITICAL",
                        "claim": "stale_boot_receipt_READY",
                        "reality": gate.get("state"),
                        "evidence": str(boot_receipt),
                    }
                )
            if prev.get("main_cortex", {}).get("ok") and not ollama.get("ok"):
                contradictions.append(
                    {
                        "class": "CRITICAL",
                        "claim": "stale_MODEL_AVAILABLE",
                        "reality": ollama.get("reason"),
                        "evidence": "rechecked_ollama",
                    }
                )
        critical = [c for c in contradictions if c.get("class") == "CRITICAL"]
        execution_authority_allowed = (
            not critical
            and bool(ollama.get("main_cortex_present"))
            and gate.get("state") == "READY_FOR_REAL_PROJECT_WORK"
        )
        review = {
            "schema": "raios.session-start-cognitive-review.v1",
            "created_at": utc_now(),
            "SYSTEM_HEALTH": {
                "wal_ok": bool(wal.get("ok")),
                "work_gate": gate.get("state"),
                "semantic": gate.get("semantic"),
            },
            "RAIOS_HEALTH": {
                "main_cortex_present": bool(ollama.get("main_cortex_present")),
                "ollama_ok": bool(ollama.get("ok")),
                "ollama_reason": ollama.get("reason"),
                "nervous": self.ccee.nervous.identity(),
            },
            "REPO_HEALTH": {
                "dirty": bool(dirty.stdout.strip()),
                "git_integrity": dirty.integrity,
                "branch": encoding_safe_run(["git", "branch", "--show-current"], cwd=self.repo).stdout.strip(),
            },
            "LEARNING_DELTA": {
                "meta_records": len(self.ccee.meta.records),
                "policy_candidates": self.ccee.meta.policy_candidates(),
                "lessons_retrieved": len(self.retrieved_lessons()),
                "encoding_class_taught": self.encoding_class_taught(),
            },
            "NEW_CAPABILITIES": [
                "d1-d11",
                "cognitive-turn-v1",
                "live-training-loop",
                "lesson-adapted-strategy",
                "hit-classification-v9-brain-negative-control",
                "meta-learning-ledger-restore",
                "governed-executor-bridge-observe-only",
                "session-contradiction-freeze",
            ],
            "REGRESSIONS": [],
            "CONTRADICTIONS": contradictions,
            "execution_authority_allowed": execution_authority_allowed,
            "BLOCKERS": blockers,
            "RESUMABLE_TASKS": queues,
            "PRIORITY_NEXT_ACTIONS": [
                "ask_raios_first_on_next_repair",
                "do_not_open_work_gate_without_qwen",
                "resolve_critical_contradictions_before_authority",
            ],
            "canonical": False,
        }
        path = Path(self.ccee.root) / "SESSION-START-COGNITIVE-REVIEW.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(review) + "\n", encoding="utf-8")
        reports = native_root(self.repo) / "reports" / "SESSION-START-COGNITIVE-REVIEW.json"
        loop_root = (native_root(self.repo) / "ccee" / "var" / "loop").resolve()
        if Path(self.ccee.root).resolve() == loop_root:
            reports.parent.mkdir(parents=True, exist_ok=True)
            reports.write_text(canonical_json(review) + "\n", encoding="utf-8")
            review["reports_path"] = str(reports)
        review["path"] = str(path)
        return review


def main(argv: list[str] | None = None) -> int:
    import sys
    from .engine import CCEE as Engine

    args = list(sys.argv[1:] if argv is None else argv)
    repo = repo_root_from()
    native = native_root(repo)
    root = native / "ccee" / "var" / "loop"
    engine = Engine(root, repo_root=repo)
    loop = LiveCognitiveLoop(engine, repo)
    try:
        cmd = args[0] if args else "review"
        if cmd == "review":
            out = loop.continuity_review()
        elif cmd == "ask":
            task_id = args[args.index("--task-id") + 1]
            intent = args[args.index("--intent") + 1]
            raw = loop.ask_raios(task_id=task_id, intent=intent)
            diagnosis = (raw.get("result") or {}).get("gateway_diagnosis") or {}
            out = {
                "task_id": raw.get("task_id"),
                "attempt": raw.get("attempt"),
                "actor": raw.get("actor"),
                "queue": raw.get("queue"),
                "confidence": raw.get("confidence"),
                "hit_count": len((raw.get("result") or {}).get("hits") or []),
                "unsafe_preview": (raw.get("result") or {}).get("unsafe_preview") or [],
                "buckets": {k: len(v) for k, v in ((raw.get("result") or {}).get("buckets") or {}).items()},
                "strategy": (raw.get("result") or {}).get("strategy"),
                "action_taken": raw.get("action_taken"),
                "plan": raw.get("plan"),
                "hypothesis": raw.get("hypothesis"),
                "d4_family": diagnosis.get("d4_family"),
                "live_status_bypasses_pass_detector": diagnosis.get("live_status_bypasses_pass_detector"),
                "student_claims": diagnosis.get("student_claims"),
                "turn_id": raw.get("turn_id"),
            }
        elif cmd == "queues":
            out = loop.queues_snapshot()
        else:
            raise FailClosed(f"UNKNOWN_LOOP_CMD:{cmd}")
        sys.stdout.write(canonical_json({"overall_status": "STRUCTURED", "payload": out}) + "\n")
        return 0
    except FailClosed as exc:
        sys.stdout.write(canonical_json({"overall_status": "FAILED", "error": str(exc)}) + "\n")
        return 1
    finally:
        engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
