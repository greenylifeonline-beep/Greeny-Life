from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))

from raios_mcp import gateway


def test_scoped_read_result_returns_text_and_metadata():
    source = {
        "INVOKED": True,
        "CAPABILITY": "engineering.scoped_repo_task",
        "OPERATION": "READ_FILE",
        "PATH": ".ai-os/MODEL-REGISTRY.json",
        "SHA256": "a" * 64,
        "SIZE": 12,
        "BRANCH": "ai-evolution-202608051809",
        "HEAD_BEFORE": "b" * 40,
        "TEXT": "model=example",
    }
    out = gateway._execution_result_projection(source)
    assert out is not None
    assert out["CONTENT_RETURNED"] is True
    assert out["TEXT"] == "model=example"
    assert out["PATH"] == source["PATH"]
    assert out["SHA256"] == source["SHA256"]
    assert out["TRUNCATED"] is False
    assert out["RETURNED_CHARS"] == len("model=example")


def test_scoped_read_result_is_bounded():
    raw = "x" * (gateway.EXECUTION_RESULT_MAX_CHARS + 100)
    out = gateway._execution_result_projection(
        {"INVOKED": True, "OPERATION": "READ_FILE", "TEXT": raw}
    )
    assert out is not None
    assert out["CONTENT_RETURNED"] is True
    assert out["TRUNCATED"] is True
    assert len(out["TEXT"]) == gateway.EXECUTION_RESULT_MAX_CHARS
    assert out["RETURNED_CHARS"] == gateway.EXECUTION_RESULT_MAX_CHARS
    assert out["SOURCE_CHARS"] == len(raw)


def test_scoped_read_result_redacts_credentials():
    raw = (
        "api_key=ABCDEFGHIJKLMNOPQRST\n"
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n"
        "DATABASE_URL=postgres://user:pass@example/db\n"
    )
    out = gateway._execution_result_projection(
        {"INVOKED": True, "OPERATION": "READ_FILE", "TEXT": raw}
    )
    text = out["TEXT"]
    assert "ABCDEFGHIJKLMNOPQRST" not in text
    assert "abcdefghijklmnopqrstuvwxyz123456" not in text
    assert "postgres://user:pass@example/db" not in text
    assert "[REDACTED]" in text


def test_gateway_execution_response_includes_transient_result_not_persisted_text():
    source = (ROOT / "scripts" / "ai-os" / "raios_mcp" / "gateway.py").read_text(encoding="utf-8")
    assert '"result": client_result' in source
    assert 'receipt["RESULT_CONTENT_PERSISTED"] = False' in source
    assert 'if key != "TEXT"' in source
