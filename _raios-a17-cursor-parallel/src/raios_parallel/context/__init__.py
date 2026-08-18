"""Production-quality context compiler with budget, contradictions, and exclusion manifest."""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, sha256_obj, utc_now


def tokens(text: str) -> int:
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
    ) -> dict[str, Any]:
        if budget_tokens <= 0:
            raise FailClosed("CONTEXT_BUDGET_INVALID")
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
        items = []
        for kind, rows in sources.items():
            for idx, row in enumerate(rows):
                text = row.get("text") if isinstance(row, dict) else str(row)
                if isinstance(row, dict) and not text:
                    text = canonical_json(row)
                text = str(text)
                contradiction = bool(isinstance(row, dict) and row.get("contradiction"))
                score = 0.0
                if isinstance(row, dict):
                    score = (
                        0.22 * float(row.get("relevance", 0.5))
                        + 0.18 * float(row.get("authority", 0.5))
                        + 0.12 * float(row.get("freshness", 0.5))
                        + 0.12 * float(row.get("capability_match", 0.5))
                        + 0.10 * float(row.get("reuse_value", 0.5))
                        + 0.08 * (1.0 - float(row.get("risk", 0.5)))
                        + (0.18 if contradiction else 0.0)
                    )
                digest = sha256_obj({"kind": kind, "text": text})
                items.append(
                    {
                        "item_id": str(row.get("id") if isinstance(row, dict) else f"{kind}:{idx}"),
                        "kind": kind,
                        "text": text,
                        "score": score,
                        "contradiction": contradiction,
                        "sha256": digest,
                        "tokens": tokens(text),
                        "provenance": str(row.get("provenance", kind) if isinstance(row, dict) else kind),
                    }
                )
        unique: dict[str, dict[str, Any]] = {}
        for item in items:
            prev = unique.get(item["sha256"])
            if prev is None or item["score"] > prev["score"]:
                unique[item["sha256"]] = item
        ranked = sorted(unique.values(), key=lambda x: x["score"], reverse=True)
        included, excluded, used = [], [], 0
        for item in ranked:
            if used + item["tokens"] <= budget_tokens:
                included.append(item)
                used += item["tokens"]
            else:
                excluded.append({**item, "text": item["text"][:160], "reason": "BUDGET_EXCEEDED"})
        if any(i["contradiction"] for i in ranked) and not any(i["contradiction"] for i in included):
            forced = next(i for i in ranked if i["contradiction"])
            while included and used + forced["tokens"] > budget_tokens:
                dropped = included.pop()
                used -= int(dropped["tokens"])
                excluded.append({**dropped, "reason": "EVICTED_FOR_CONTRADICTION"})
            included.append({**forced, "forced": True})
            used += int(forced["tokens"])
            excluded = [e for e in excluded if e["item_id"] != forced["item_id"]]
        if used > budget_tokens and included:
            last = included[-1]
            keep = max(1, len(last["text"]) - (used - budget_tokens) * 4)
            last["text"] = last["text"][:keep]
            last["tokens"] = tokens(last["text"])
            used = sum(int(i["tokens"]) for i in included)
        return {
            "manifest_id": deterministic_id("ctx", str(budget_tokens)),
            "included": included,
            "excluded": excluded,
            "included_refs": [i["sha256"] for i in included],
            "excluded_refs": [e["sha256"] for e in excluded],
            "budget_tokens": budget_tokens,
            "used_tokens": used,
            "contradictions_preserved": any(i.get("contradiction") for i in included),
            "blind_dump": False,
            "created_at": utc_now(),
        }
