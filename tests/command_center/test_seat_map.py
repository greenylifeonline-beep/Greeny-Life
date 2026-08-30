import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_exactly_twelve_council_members_and_worker_is_external():
    data=json.loads((ROOT/".ai-os/mcp/SEAT-MAP.json").read_text(encoding="utf-8"))
    seats=data["seats"]
    assert data["seat_count"]==12
    assert list(seats)==[f"C{i}" for i in range(1,13)]
    assert all(row["member"] is True for row in seats.values())
    worker=data["worker"]
    assert worker["id"]=="RAIOS-WORKER"
    assert worker["council_member"] is False
    assert worker["c_code"] is None
    assert worker["vote"] is False and worker["opinion"] is False
    assert worker["owner"]=="RAIOS_SYSTEM"
    assert worker["permanent_lock"] is False
    assert "RAIOS-WORKER" not in seats
    assert "C7" in seats
