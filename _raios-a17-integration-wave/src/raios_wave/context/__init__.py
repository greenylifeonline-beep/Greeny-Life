"""Context compiler with explicit budget, ranking, provenance, and exclusion manifest."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..identity import canonical_json, deterministic_id, sha256_obj, utc_now


@dataclass
class ContextItem:
    item_id: str
    kind: str
    text: str
    priority: float
    freshness: float
    authority: float
    relevance: float
    provenance: str
    contradiction: bool = False
    sha256: str = ""

    def score(self) -> float:
        contradiction_bonus = 0.15 if self.contradiction else 0.0
        return (
            0.30 * self.priority
            + 0.20 * self.relevance
            + 0.15 * self.authority
            + 0.10 * self.freshness
            + contradiction_bonus
        )


@dataclass
class CompiledContext:
    manifest_id: str
    included: list[dict[str, Any]] = field(default_factory=list)
    excluded: list[dict[str, Any]] = field(default_factory=list)
    budget_tokens: int = 0
    used_tokens: int = 0
    created_at: str = field(default_factory=utc_now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "included": self.included,
            "excluded": self.excluded,
            "budget_tokens": self.budget_tokens,
            "used_tokens": self.used_tokens,
            "created_at": self.created_at,
            "blind_dump": False,
        }


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


class ContextCompiler:
    def compile(
        self,
        *,
        task: dict[str, Any],
        observations: list[dict[str, Any]] | None = None,
        memory: list[dict[str, Any]] | None = None,
        rkg: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        experience: list[dict[str, Any]] | None = None,
        failures: list[dict[str, Any]] | None = None,
        policies: list[dict[str, Any]] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        learning_state: list[dict[str, Any]] | None = None,
        budget_tokens: int = 1024,
        include_contradictions: bool = True,
    ) -> dict[str, Any]:
        if budget_tokens <= 0:
            from ..identity import FailClosed

            raise FailClosed("CONTEXT_BUDGET_INVALID")
        items: list[ContextItem] = []
        sources = {
            "task": [task],
            "observation": observations or [],
            "memory": memory or [],
            "rkg": rkg or [],
            "skill": skills or [],
            "experience": experience or [],
            "failure": failures or [],
            "policy": policies or [],
            "evidence": evidence or [],
            "learning_state": learning_state or [],
        }
        for kind, rows in sources.items():
            for idx, row in enumerate(rows):
                text = row.get("text") if isinstance(row, dict) else str(row)
                if isinstance(row, dict) and not text:
                    text = canonical_json(row)
                text = str(text)
                contradiction = bool(isinstance(row, dict) and row.get("contradiction"))
                if contradiction and not include_contradictions:
                    continue
                item = ContextItem(
                    item_id=str((row or {}).get("id") if isinstance(row, dict) else f"{kind}:{idx}"),
                    kind=kind,
                    text=text,
                    priority=float((row or {}).get("priority", 0.5) if isinstance(row, dict) else 0.5),
                    freshness=float((row or {}).get("freshness", 0.5) if isinstance(row, dict) else 0.5),
                    authority=float((row or {}).get("authority", 0.5) if isinstance(row, dict) else 0.5),
                    relevance=float((row or {}).get("relevance", 0.5) if isinstance(row, dict) else 0.5),
                    provenance=str((row or {}).get("provenance", kind) if isinstance(row, dict) else kind),
                    contradiction=contradiction,
                )
                item.sha256 = sha256_obj({"text": item.text, "kind": item.kind, "provenance": item.provenance})
                items.append(item)
        # dedupe by sha256 keeping higher score
        unique: dict[str, ContextItem] = {}
        for item in items:
            prev = unique.get(item.sha256)
            if prev is None or item.score() > prev.score():
                unique[item.sha256] = item
        ranked = sorted(unique.values(), key=lambda item: item.score(), reverse=True)
        compiled = CompiledContext(
            manifest_id=deterministic_id("ctx", str(budget_tokens), task.get("id", "task") if isinstance(task, dict) else "task"),
            budget_tokens=budget_tokens,
        )
        used = 0
        seen_contradiction = False
        for item in ranked:
            cost = estimate_tokens(item.text)
            entry = {
                "item_id": item.item_id,
                "kind": item.kind,
                "tokens": cost,
                "score": item.score(),
                "provenance": item.provenance,
                "contradiction": item.contradiction,
                "sha256": item.sha256,
                "text": item.text,
            }
            if item.contradiction and include_contradictions and not seen_contradiction:
                # contradictions that are relevant are forced into budget if possible
                if used + cost <= budget_tokens or not compiled.included:
                    compiled.included.append(entry)
                    used += cost
                    seen_contradiction = True
                    continue
            if used + cost <= budget_tokens:
                compiled.included.append(entry)
                used += cost
                if item.contradiction:
                    seen_contradiction = True
            else:
                reason = "BUDGET_EXCEEDED"
                compiled.excluded.append({**entry, "text": entry["text"][:200], "reason": reason})
        compiled.used_tokens = used
        if include_contradictions:
            remaining = [item for item in ranked if item.contradiction]
            if remaining and not any(row.get("contradiction") for row in compiled.included):
                forced = remaining[0]
                cost = estimate_tokens(forced.text)
                while compiled.included and compiled.used_tokens + cost > budget_tokens:
                    dropped = compiled.included.pop()
                    compiled.used_tokens -= int(dropped["tokens"])
                    compiled.excluded.append({**dropped, "text": str(dropped.get("text") or "")[:200], "reason": "EVICTED_FOR_CONTRADICTION"})
                if compiled.used_tokens + cost <= budget_tokens or not compiled.included:
                    compiled.included.append(
                        {
                            "item_id": forced.item_id,
                            "kind": forced.kind,
                            "tokens": cost,
                            "score": forced.score(),
                            "provenance": forced.provenance,
                            "contradiction": True,
                            "sha256": forced.sha256,
                            "text": forced.text[: max(1, (budget_tokens - compiled.used_tokens) * 4)] if compiled.used_tokens + cost > budget_tokens else forced.text,
                            "forced": True,
                        }
                    )
                    compiled.used_tokens += estimate_tokens(compiled.included[-1]["text"])
                    compiled.excluded = [row for row in compiled.excluded if row["item_id"] != forced.item_id]
        if compiled.used_tokens > budget_tokens and compiled.included:
            # last-resort trim of the forced text so the compiler never silently overruns
            last = compiled.included[-1]
            overflow = compiled.used_tokens - budget_tokens
            if overflow > 0 and last.get("forced"):
                keep_chars = max(1, len(last["text"]) - overflow * 4)
                last["text"] = last["text"][:keep_chars]
                last["tokens"] = estimate_tokens(last["text"])
                compiled.used_tokens = sum(int(row["tokens"]) for row in compiled.included)
        result = compiled.as_dict()
        result["deduplicated"] = len(items) - len(unique)
        result["compressed"] = True
        return result
