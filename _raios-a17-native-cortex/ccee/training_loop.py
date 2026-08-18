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

from .config import FailClosed, canonical_json, deterministic_id, repo_root_from, sha256_obj, utc_now
from .process_kernel import encoding_safe_run
from .repair_memory import KERNEL_REPAIR_ID
from .root_cause import classify_failure
from .schemas import CognitiveTurn, CriticScore, QueueName
from .work_gate import WorkGate

MAX_ATTEMPTS = 3
SKIP_HINTS = ("/archive/", "\\.architecture-backups\\", "/node_modules/", "/.git/")


def _skip(path: str) -> bool:
    lowered = path.replace("\\", "/")
    return any(h.replace("\\", "/") in lowered for h in SKIP_HINTS)


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
        strategy = strategy or {1: "naive_repo_rg", 2: "exclude_archive", 3: "expand_popen_check_output"}[attempt]
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
        obs = encoding_safe_run(argv, cwd=self.repo, timeout=45.0)
        lines = [ln for ln in obs.stdout.splitlines() if ln.strip()]
        if strategy != "naive_repo_rg":
            lines = [ln for ln in lines if not _skip(ln)]
        family = classify_failure(
            {
                "integrity": obs.integrity,
                "decode_replaced": obs.decode_replaced,
                "child_exit": obs.returncode,
                "printed_pass": False,
                "failed": obs.returncode not in {0, 1},
            }
        )
        memory = self.ccee.nervous.repair_memory.get(KERNEL_REPAIR_ID)
        hits = lines[:60]
        unsafe = [
            h
            for h in hits
            if ("text=True" in h or "errors='ignore'" in h or 'errors="ignore"' in h)
            and "errors='strict'" not in h
            and 'errors="strict"' not in h
            and "forbids brain.py" not in h
        ]
        turn = CognitiveTurn(
            task_id=task_id,
            attempt=attempt,
            actor="RAIOS",
            intent=intent,
            observations=[
                {"strategy": strategy, "hit_count": len(lines), "shown": len(hits), "returncode": obs.returncode},
            ],
            evidence=[
                {"tool": "rg", "kernel": "d1", "stdout_sha256": obs.stdout_sha256, "integrity": obs.integrity},
                {"lease_id": lease["lease_id"]},
            ],
            hypothesis=[
                {"family": family or "UNICODE_DECODE", "repair_id": KERNEL_REPAIR_ID if memory else None},
                {"claim": "remaining locale-decoded subprocess callers are the same D1 class"},
            ],
            plan=[
                "search subprocess callers with D1 rg",
                "filter archive on retry if naive search is noisy",
                "reconnect remaining callers to encoding_safe_run",
                "negative control: latin1 0xe9 must not raise; PASS+exit1 must fail-closed",
            ],
            action_requested=[
                {"tool": "d1.encoding_safe_run", "targets": unsafe[:20], "mutating": True, "requires": "HUMAN_OR_READY_GATE"},
            ],
            permission_scope=["repository reads", "structural search"],
            action_taken=[
                {"tool": "rg", "argv": argv, "executed": True, "mutating": False},
            ],
            result={
                "ok": obs.returncode in {0, 1},
                "hits": hits,
                "unsafe_preview": unsafe[:20],
                "strategy": strategy,
                "execution_authority": False,
            },
            confidence=0.45 if hits else 0.2,
            critic_score=0.0,
            failure_class=None if obs.returncode in {0, 1} else family,
            lesson=[],
            next_action=["cursor_critique", "reconnect_if_authorized"],
            queue="SHADOW_VALIDATION" if unsafe else "READY",
            teacher_used=False,
        )
        persisted = self.persist_turn(turn)
        episode = self.ccee.metabolism.metabolize(
            {"id": task_id, "intent": intent, "input": {"strategy": strategy}},
            {"ok": bool(turn.result.get("ok")), "plan": turn.plan, "teacher_used": False, "success_score": 0.4},
            {"observations": turn.observations, "actions": turn.action_taken, "tool_calls": turn.action_taken, "uncertainty": 0.4},
        )
        persisted["episode_id"] = episode["episode_id"]
        if attempt >= MAX_ATTEMPTS and not unsafe:
            return self.block(task_id, intent, "NO_UNSAFE_HITS_AFTER_THREE")
        return persisted

    def _search_argv(self, strategy: str) -> list[str]:
        glob = ["--glob", "*.py"]
        if strategy == "naive_repo_rg":
            return ["rg", "-n", "--max-count", "200", *glob, r"subprocess\.(run|Popen|check_output|check_call)", str(self.repo)]
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
                str(self.repo),
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
                str(self.repo),
            ]
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
        from .config import native_root

        boot_gate = native_root(self.repo) / "ccee" / "var" / "boot" / "nervous" / "work_gate.json"
        if boot_gate.is_file():
            gate = json.loads(boot_gate.read_text(encoding="utf-8"))
        else:
            gate = WorkGate(self.ccee.nervous.gate.path).read()
        wal = self.ccee.wal.verify_chain()
        dirty = encoding_safe_run(["git", "status", "--porcelain"], cwd=self.repo)
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
            },
            "NEW_CAPABILITIES": ["d1-d11", "cognitive-turn-v1", "live-training-loop"],
            "REGRESSIONS": [],
            "BLOCKERS": [b for b in ["MAIN_CORTEX_UNREACHABLE"] if not ollama.get("ok")],
            "RESUMABLE_TASKS": self.queues_snapshot(),
            "PRIORITY_NEXT_ACTIONS": [
                "ask_raios_first_on_next_repair",
                "do_not_open_work_gate_without_qwen",
            ],
            "canonical": False,
        }
        path = Path(self.ccee.root) / "SESSION-START-COGNITIVE-REVIEW.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(review) + "\n", encoding="utf-8")
        review["path"] = str(path)
        return review


def main(argv: list[str] | None = None) -> int:
    import sys
    from .config import native_root
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
            out = {
                "task_id": raw.get("task_id"),
                "attempt": raw.get("attempt"),
                "actor": raw.get("actor"),
                "queue": raw.get("queue"),
                "confidence": raw.get("confidence"),
                "hit_count": len((raw.get("result") or {}).get("hits") or []),
                "unsafe_preview": (raw.get("result") or {}).get("unsafe_preview") or [],
                "action_taken": raw.get("action_taken"),
                "plan": raw.get("plan"),
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
