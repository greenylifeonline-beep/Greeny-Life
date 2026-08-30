from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_paid_rag_stack_is_not_the_live_injector():
    req = (ROOT / "requirements-neurolingua.txt").read_text(encoding="utf-8").lower()
    for banned in ("langchain", "openai", "chromadb", "chroma", "faiss", "dify", "flowise"):
        assert banned not in req
    index = ROOT / "scripts" / "ai-os" / "raios_c5_index.py"
    text = index.read_text(encoding="utf-8")
    assert "INVERTED_INDEX_NE_UNLOADED_EMBEDDING" in text
    fill = ROOT / "scripts" / "ai-os" / "raios_c5_mind_fill.ps1"
    assert fill.is_file()
