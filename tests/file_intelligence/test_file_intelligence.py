from __future__ import annotations

import hashlib
import json
from pathlib import Path

from raios.file_intelligence import classify_authority, classify_file, extract_text, tool_health


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_json_parser_probe_and_source_immutability(tmp_path: Path):
    path = tmp_path / "sample.json"
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    before = digest(path)
    result = classify_file(path)
    assert result["file_class"] == "DATA"
    assert result["language"] == "json"
    assert result["immutable_source"] is True
    assert digest(path) == before


def test_pdf_signature_beats_extension(tmp_path: Path):
    path = tmp_path / "not-a-pdf.txt"
    path.write_bytes(b"%PDF-1.7\nfake")
    result = classify_file(path)
    assert result["file_class"] == "DOCUMENT"
    assert result["language"] == "pdf"
    assert result["detector"] == "signature"


def test_extension_is_hint_not_authority(tmp_path: Path):
    path = tmp_path / "blob.py"
    path.write_bytes(b"\x00\x01\x02\x03")
    result = classify_file(path)
    assert result["file_class"] == "UNKNOWN"
    assert result["detector"] == "none"


def test_authority_dimensions_are_independent():
    current = classify_authority("C:/repo/canonical/data/master_products.json", deterministic_ok=True)
    historical = classify_authority("C:/repo/archive/old/report.json", deterministic_ok=True)
    assert current.authority_class == "CERTIFIED_STATE"
    assert current.temporal_scope == "CURRENT"
    assert current.verification_state == "PARTIALLY_VERIFIED"
    assert historical.authority_class == "HISTORICAL_EVIDENCE"
    assert historical.temporal_scope == "HISTORICAL"
    assert historical.knowledge_state == "SUPERSEDED"


def test_tool_health_never_installs_or_enables_ocr():
    health = tool_health()
    assert health["mode"] == "READ_ONLY"
    assert health["automatic_install"] is False
    assert health["llm_default_parser"] is False
    assert health["ocr_enabled"] is False


def test_plain_text_extract_is_read_only(tmp_path: Path):
    path = tmp_path / "note.md"
    path.write_text("hello", encoding="utf-8")
    before = digest(path)
    result = extract_text(path)
    assert result["status"] == "EXTRACTED"
    assert result["text"] == "hello"
    assert result["ocr"] is False
    assert digest(path) == before
