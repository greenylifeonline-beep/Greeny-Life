import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_train import COMMAND, KEEPERS, PLATFORMS, host_id  # noqa: E402


def test_mesh_lists_every_platform_and_one_command():
    ids = {row["id"] for row in PLATFORMS}
    assert ids == {
        "cursor-vm",
        "repair-windows",
        "colab",
        "kaggle",
        "github-actions",
        "huggingface-hub",
        "huggingface-jobs",
        "c5-git",
    }
    assert COMMAND == "python3 scripts/ai-os/raios_c5_train.py"
    assert any(name == "speak" for name, _ in KEEPERS)
    assert any(name == "kae" for name, _ in KEEPERS)
    assert any(name == "toc" for name, _ in KEEPERS)
    assert any(name == "mind-fill" for name, _ in KEEPERS)
    assert any(name == "foundation" for name, _ in KEEPERS)
    assert any(name == "p0" for name, _ in KEEPERS)
    assert any(name == "phase0" for name, _ in KEEPERS)
    assert any(name == "book" for name, _ in KEEPERS)
    assert any(name == "reality" for name, _ in KEEPERS)
    assert host_id("local-or-cursor") == "cursor-vm"
    assert host_id("colab") == "colab"
    assert sum(1 for row in PLATFORMS if row["is_c5"]) == 1
