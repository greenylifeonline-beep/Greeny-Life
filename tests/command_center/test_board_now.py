import json
from pathlib import Path

from raios.command_center.board_now import hanging_work, now_from_projected, now_tasks, render_md
from raios.command_center.council_board import CouncilBoard


def test_now_slice_is_not_tail_dump_or_full_ledger():
    tasks = [
        {"id": "OLD-DONE", "title": "done", "status": "DONE"},
        {"id": "LOW-READY", "title": "low ready", "status": "READY", "scheduler_priority": "LOW"},
        {"id": "HIGH-READY", "title": "high ready", "status": "READY", "scheduler_priority": "HIGH"},
        {"id": "DOING", "title": "in flight", "status": "IN_PROGRESS", "claimed_by": "C2@AG", "scheduler_priority": "CRITICAL"},
        {"id": "C6-GATE", "title": "needs C6", "status": "BLOCKED", "blocker": "C6_NOT_LIVE_BOUND", "board_visibility": "REQUIRED"},
        {"id": "GOAL-ROW", "title": "named goal", "status": "READY", "entity": "GOAL"},
    ]
    for i in range(20):
        tasks.append({"id": f"QUEUE-{i:02d}", "title": "queued high", "status": "READY", "scheduler_priority": "HIGH"})
    for i in range(20):
        tasks.append({"id": f"TAIL-{i:02d}", "title": "tail", "status": "DONE"})
    rows = now_tasks(tasks)
    ids = {r["id"] for r in rows}
    assert "DOING" in ids and "C6-GATE" in ids and "HIGH-READY" in ids and "GOAL-ROW" in ids
    assert "OLD-DONE" not in ids and "LOW-READY" not in ids
    assert "TAIL-19" not in ids
    assert rows[0]["id"] == "DOING"
    queued = [r for r in rows if r["status"] == "READY" and not r["visible"]]
    assert len(queued) == 8 and queued[0]["id"] == "HIGH-READY"
    assert "QUEUE-19" not in ids
    md = render_md({"active_program_id": "RAIOS-CAPABILITY-EVOLUTION-202609-202703"}, rows)
    assert "TASKS.json" in md and "NOW.md" in md and "DOING" in md


def test_snapshot_now_is_narrower_than_full_projection(tmp_path):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    tasks = {
        "active_program_id": "PROG-1",
        "tasks": [
            {"id": "DONE", "title": "done", "status": "DONE", "dependencies": []},
            {"id": "NEXT", "title": "next", "status": "READY", "dependencies": ["DONE"],
             "allowed_agents": ["C2"], "scheduler_priority": "LOW"},
            {"id": "LIVE", "title": "live", "status": "IN_PROGRESS", "claimed_by": "C2@AG",
             "scheduler_priority": "CRITICAL", "dependencies": []},
        ],
    }
    (repo / ".ai-os/state/TASKS.json").write_text(json.dumps(tasks), encoding="utf-8")
    board = CouncilBoard(repo, tmp_path / "presence.json")
    out = board.snapshot()
    now_ids = {r["id"] for r in out["now"]}
    all_ids = {r["id"] for r in out["tasks"]}
    assert out["now_ne_full_ledger"] is True
    assert now_ids == {"LIVE"}
    assert all_ids == {"DONE", "NEXT", "LIVE"}
    projected = now_from_projected(out["tasks"], tasks["tasks"])
    assert [r["id"] for r in projected] == ["LIVE"]


def test_now_rows_keep_independent_lifecycle_states():
    tasks = [{
        "id": "DOING",
        "title": "in flight",
        "status": "IN_PROGRESS",
        "claimed_by": "C2@AG",
        "scheduler_priority": "CRITICAL",
        "program_id": "RAIOS-CAPABILITY-EVOLUTION-202609-202703",
        "project_id": "UCF",
        "test_state": "UNKNOWN",
        "review_state": "UNKNOWN",
        "deployment_state": "UNKNOWN",
    }]
    rows = now_tasks(tasks)
    assert rows[0]["id"] == "DOING"
    assert rows[0]["program"] == "RAIOS-CAPABILITY-EVOLUTION-202609-202703"
    assert rows[0]["project"] == "UCF"
    assert rows[0]["lifecycle"]["collapsed_to_done"] is False
    assert rows[0]["lifecycle"]["COMPLETE"] == "UNKNOWN"
    assert rows[0]["status"] == "IN_PROGRESS"


def test_hanging_work_notifies_system_without_mutating_ledger():
    tasks = [
        {"id": "DONE-1", "status": "DONE"},
        {"id": "RUN-STALE", "status": "IN_PROGRESS", "claimed_by": "C2", "updated_at": "2026-01-01T00:00:00+00:00"},
        {"id": "BLOCK-1", "status": "BLOCKED", "blocker": "AWAITING_C1"},
        {"id": "READY-FREE", "status": "READY"},
        {"id": "READY-OWNED", "status": "READY", "claimed_by": "C6"},
    ]
    out = hanging_work(tasks, stale_after_hours=24)
    assert out["schema"] == "raios.hanging-work.v1"
    assert out["mutated_tasks_ledger"] is False
    assert out["system_informed"] is True
    assert out["must_complete_or_notify"] is True
    assert out["open_count"] == 4
    assert out["in_progress_count"] == 1
    assert out["blocked_count"] == 1
    assert "RUN-STALE" in out["stale_in_progress"]
    assert "READY-FREE" in [row["id"] for row in out["items"] if row["status"] == "READY" and not row["claimed_by"]]
    assert "DONE-1" not in {row["id"] for row in out["items"]}


def test_load_tasks_document_caches_by_mtime(tmp_path):
    from raios.command_center.board_now import load_tasks_document
    path = tmp_path / "TASKS.json"
    path.write_text('{"tasks":[{"id":"A","status":"READY"}]}', encoding="utf-8")
    first = load_tasks_document(path, {"tasks": []})
    second = load_tasks_document(path, {"tasks": []})
    assert first is second
    assert first["tasks"][0]["id"] == "A"
    path.write_text('{"tasks":[{"id":"B","status":"BLOCKED"}]}', encoding="utf-8")
    third = load_tasks_document(path, {"tasks": []})
    assert third is not first
    assert third["tasks"][0]["id"] == "B"
