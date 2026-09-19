import json
from pathlib import Path

from raios.command_center.board_now import now_from_projected, now_tasks, render_md
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
