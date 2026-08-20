"""NeuroLingua configuration loader.

Reads ``configs/neuro_lingua/`` (NL-0 contract) and optionally overlays the
existing root ``config.yaml`` LLM block without mutating it. ``config.yaml``
is a BOUND.md danger zone; this loader is read-only toward that file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def find_repo_root(start: Path | None = None) -> Path:
    cursor = (start or Path.cwd()).resolve()
    markers = ("config.yaml", "brain.py", "configs/neuro_lingua", ".git")
    for candidate in [cursor, *cursor.parents]:
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    return cursor


@dataclass
class NeuroLinguaConfig:
    repo_root: Path
    concepts_path: Path
    locales_path: Path
    pragmatics_path: Path
    scandinavian_path: Path
    wal_path: Path
    evolution_inbox_path: Path
    offline: bool = True
    allow_llm_adjudication: bool = False
    allow_back_translation: bool = False
    host_llm_provider: str | None = None
    host_llm_model: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def config_dir(self) -> Path:
        return self.repo_root / "configs" / "neuro_lingua"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {path}")
    return loaded


def load_neuro_lingua_config(repo_root: Path | None = None) -> NeuroLinguaConfig:
    root = find_repo_root(repo_root)
    nl_dir = root / "configs" / "neuro_lingua"
    nl_cfg = _read_yaml(nl_dir / "config.yaml")

    host_cfg = _read_yaml(root / "config.yaml")
    llm = host_cfg.get("llm") if isinstance(host_cfg.get("llm"), dict) else {}

    wal_rel = nl_cfg.get(
        "wal_path",
        "intelligence/knowledge_base/neuro_lingua/cognitive_wal.jsonl",
    )
    inbox_rel = nl_cfg.get(
        "evolution_inbox_path",
        "intelligence/knowledge_base/neuro_lingua/evolution_inbox.jsonl",
    )
    kb_path = host_cfg.get("brain", {}).get("knowledge_base_path")
    if kb_path and "wal_path" not in nl_cfg:
        wal_rel = str(Path(kb_path) / "neuro_lingua" / "cognitive_wal.jsonl")
        inbox_rel = str(Path(kb_path) / "neuro_lingua" / "evolution_inbox.jsonl")

    return NeuroLinguaConfig(
        repo_root=root,
        concepts_path=nl_dir / "concepts.yaml",
        locales_path=nl_dir / "locales.yaml",
        pragmatics_path=nl_dir / "pragmatics.yaml",
        scandinavian_path=nl_dir / "scandinavian.yaml",
        wal_path=root / wal_rel,
        evolution_inbox_path=root / inbox_rel,
        offline=bool(nl_cfg.get("offline", True)),
        allow_llm_adjudication=bool(nl_cfg.get("allow_llm_adjudication", False)),
        allow_back_translation=bool(nl_cfg.get("allow_back_translation", False)),
        host_llm_provider=llm.get("provider"),
        host_llm_model=llm.get("model"),
        extra=nl_cfg,
    )
