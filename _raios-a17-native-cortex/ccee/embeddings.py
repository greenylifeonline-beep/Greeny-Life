"""Provider-neutral embedding SPI. No automatic large-model download. BM25 fallback."""
from __future__ import annotations

import math
import re
from typing import Any, Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def search(self, query: str, k: int) -> list[dict[str, Any]]: ...
    def index(self, obj: dict[str, Any]) -> None: ...
    def delete_logical(self, obj_id: str) -> None: ...
    def reindex(self) -> None: ...


class LexicalMemory:
    def __init__(self) -> None:
        self.docs: dict[str, str] = {}
        self.deleted: set[str] = set()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t.split())), float(len(t))] for t in texts]

    def index(self, obj: dict[str, Any]) -> None:
        self.docs[str(obj["id"])] = str(obj.get("text") or "")
        self.deleted.discard(str(obj["id"]))

    def delete_logical(self, obj_id: str) -> None:
        self.deleted.add(obj_id)

    def reindex(self) -> None:
        for obj_id in list(self.deleted):
            self.docs.pop(obj_id, None)
        self.deleted.clear()

    def search(self, query: str, k: int) -> list[dict[str, Any]]:
        q = _tokens(query)
        scored = []
        df: dict[str, int] = {}
        live = {i: t for i, t in self.docs.items() if i not in self.deleted}
        for text in live.values():
            for tok in set(_tokens(text)):
                df[tok] = df.get(tok, 0) + 1
        n = max(len(live), 1)
        for obj_id, text in live.items():
            tf = _tf(_tokens(text))
            score = 0.0
            for tok in q:
                if tok not in tf:
                    continue
                idf = math.log((n - df.get(tok, 0) + 0.5) / (df.get(tok, 0) + 0.5) + 1)
                score += idf * (tf[tok] * 2.2) / (tf[tok] + 1.2)
            scored.append({"id": obj_id, "score": score, "provider": "lexical_bm25"})
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:k]


def detect_local_embedding_model() -> dict[str, Any]:
    return {"available": False, "downloaded": False, "provider": "lexical_bm25"}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 2]


def _tf(tokens: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for tok in tokens:
        out[tok] = out.get(tok, 0) + 1
    return out
