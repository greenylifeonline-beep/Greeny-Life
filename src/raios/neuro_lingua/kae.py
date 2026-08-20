"""C5 Knowledge Assimilation Engine.

Not a second mind. Not a second WAL. Not LightRAG. Not a hidden-reasoning extractor.
Retiles an authorized output into reusable practice tiles, then writes DISCOVERED
candidates through the live ingest keeper.

Main Cortex stays isolated. This channel does not summon C seats.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .compress import compress_meaning

TILES = (
    "FACT",
    "RULE",
    "WHY",
    "WHEN",
    "WHEN_NOT",
    "EXAMPLE",
    "COUNTEREXAMPLE",
    "FAILURE_CASE",
    "QUIZ",
    "DECISION_CASE",
    "NOVEL_VARIANT",
    "ADVERSARIAL_VARIANT",
    "PROCEDURE",
    "TEST",
    "INVARIANT",
    "SKILL_CANDIDATE",
)

ATOM_KINDS = (
    "facts",
    "claims",
    "rules",
    "procedures",
    "decisions",
    "failures",
    "corrections",
    "examples",
    "counterexamples",
    "uncertainty",
    "provenance",
)

FORBIDDEN_SOURCE = (
    "hidden_reasoning",
    "system_prompt",
    "credentials",
    "secret",
    "private_key",
    "live_c_seat_consult",
)
SECRET_RE = re.compile(
    r"(api[_-]?key|secret|password|passwd|authorization:\s*bearer|"
    r"begin (rsa |openssh )?private key|system prompt|hidden reasoning|"
    r"chain of thought internal)",
    re.I,
)
LAW_RE = re.compile(r"\b([A-Z][A-Z0-9_]{5,})\b")
HTTP_DEMO = (
    "لا تعتبر HTTP 200 نجاحًا وظيفيًا قبل التحقق من semantic result. "
    "HTTP status alone does not prove semantic success. HTTP_2XX_NE_SEMANTIC_SUCCESS. "
    "PRINTED_SUCCESS_NE_OBSERVED_STATE_CHANGE."
)
LAWS = (
    "KAE_NE_SECOND_MIND",
    "KAE_NE_SECOND_WAL",
    "AUTHORIZED_OUTPUT_ONLY",
    "NO_HIDDEN_REASONING_EXTRACT",
    "STUDENT_NE_MAIN_CORTEX",
    "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK",
    "THIS_CHANNEL_NO_C_SEAT_CONSULT",
    "TEACHER_TOURNAMENT_NE_VOTE_NE_TRUTH",
    "ONE_ANSWER_MANY_TILES",
    "EXTERNAL_CALL_MUST_REDUCE_NEXT_CALL",
    "HTTP_2XX_NE_SEMANTIC_SUCCESS",
    "PRINTED_SUCCESS_NE_OBSERVED_STATE_CHANGE",
    "LIVE_PATH_BEFORE_NEW_LAYER",
    "REUSE_BEFORE_BUILD",
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact(text: str) -> tuple[str, bool]:
    if SECRET_RE.search(text or ""):
        return SECRET_RE.sub("[REDACTED]", text), True
    return text, False


def source_adapter(kind: str, payload: str, *, path: str | None = None) -> dict[str, Any]:
    kind = (kind or "authorized_text").strip()
    if kind in FORBIDDEN_SOURCE:
        return {
            "ok": False,
            "error": "SOURCE_FORBIDDEN",
            "kind": kind,
            "law": "AUTHORIZED_OUTPUT_ONLY",
        }
    if kind == "live_c_seat":
        return {
            "ok": False,
            "error": "THIS_CHANNEL_NO_C_SEAT_CONSULT",
            "kind": kind,
        }
    if kind == "web_live" or kind == "api_live":
        return {
            "ok": False,
            "error": "LIVE_FETCH_NOT_IN_KAE",
            "kind": kind,
            "note": "Pass an already-authorized artifact as text. KAE does not scrape.",
        }
    if path and ("RAIOS/V9" in path.replace("\\", "/") or path.endswith(".env")):
        return {"ok": False, "error": "SOURCE_LOCKED_OR_SECRET", "path": path}
    if path:
        from .kae_libraries import allowed as path_allowed

        if not path_allowed(path):
            return {"ok": False, "error": "SOURCE_LOCKED_OR_SECRET", "path": path}
    cleaned, redacted = redact(payload or "")
    return {
        "ok": True,
        "kind": kind,
        "path": path,
        "text": cleaned,
        "redacted": redacted,
        "sha256": _sha(cleaned),
        "consult_used": False,
    }


def extract_atoms(text: str) -> dict[str, Any]:
    laws = []
    for match in LAW_RE.finditer(text or ""):
        token = match.group(1)
        if token not in laws and token not in {"HTTP", "POST", "JSON"}:
            laws.append(token)
    compressed = compress_meaning(text)
    facts = []
    if "http" in text.lower() and ("200" in text or "2xx" in text.lower()):
        facts.append("HTTP status alone does not prove semantic success.")
    first = (text or "").strip().split("\n")[0].strip()
    if first and first not in facts:
        facts.append(first[:240])
    return {
        "facts": facts[:8],
        "claims": facts[:8],
        "rules": laws[:12],
        "procedures": [],
        "decisions": laws[:8],
        "failures": ["false_positive_http"] if "200" in text else [],
        "corrections": [],
        "examples": [],
        "counterexamples": [],
        "uncertainty": ["unverified_until_replay"],
        "provenance": {"sha256": _sha(text or ""), "authorized": True},
        "compression": compressed.get("pattern") or {},
        "word_list": False,
    }


def _http_tiles() -> dict[str, str]:
    return {
        "FACT": "HTTP status alone does not prove semantic success.",
        "RULE": "HTTP_2XX_NE_SEMANTIC_SUCCESS",
        "WHY": "A server can print 2xx while the body, mutation, or observed state failed.",
        "WHEN": "After any mutating HTTP call before treating it as done.",
        "WHEN_NOT": "Do not skip semantic checks because the status looked green.",
        "EXAMPLE": "POST returns 200, body.success=false. Conclude: not a functional success.",
        "COUNTEREXAMPLE": "POST returns 201, success=true, but entity absent afterward.",
        "FAILURE_CASE": "Printed PASS / HTTP 200 with no observed state change.",
        "QUIZ": "POST returns 200, body.success=false. What should C5 conclude?",
        "DECISION_CASE": "Reject the mutation as unproven. Do not promote. Do not print PASS.",
        "NOVEL_VARIANT": "GET 200 with stale cached body while the live row is gone.",
        "ADVERSARIAL_VARIANT": "Server returns 200 with a malformed body.",
        "PROCEDURE": "request → inspect HTTP → parse body → semantic validation → observe state → compare before/after",
        "TEST": "Can C5 reject a false positive?",
        "INVARIANT": "PRINTED_SUCCESS_NE_OBSERVED_STATE_CHANGE",
        "SKILL_CANDIDATE": "verify_semantic_mutation",
    }


def retile(text: str, atoms: dict[str, Any] | None = None) -> dict[str, str]:
    atoms = atoms or extract_atoms(text)
    lower = (text or "").lower()
    if "http" in lower and ("semantic" in lower or "وظيفي" in text or "2xx" in lower or "200" in text):
        return _http_tiles()
    law = (atoms.get("rules") or ["UNNAMED_RULE"])[0]
    fact = (atoms.get("facts") or [text[:200]])[0]
    pattern = atoms.get("compression") or {}
    return {
        "FACT": fact,
        "RULE": law,
        "WHY": f"Reuse compressed pattern {pattern} instead of re-calling a teacher.",
        "WHEN": "When a similar claim appears again.",
        "WHEN_NOT": "When evidence is missing or contradicted.",
        "EXAMPLE": fact,
        "COUNTEREXAMPLE": f"Same surface as {law} but observed state does not change.",
        "FAILURE_CASE": "Treat a printed success as proven knowledge.",
        "QUIZ": f"What fails if C5 trusts this without replay? {law}",
        "DECISION_CASE": "Keep DISCOVERED. Do not promote. Replay before memory.",
        "NOVEL_VARIANT": "Same rule on a new locale or company.",
        "ADVERSARIAL_VARIANT": "Malformed or misleading success print.",
        "PROCEDURE": "observe → extract → retile → contradict → replay → ingest DISCOVERED",
        "TEST": "Can C5 reuse the rule on an unseen variant?",
        "INVARIANT": law,
        "SKILL_CANDIDATE": "apply_" + re.sub(r"[^a-z0-9]+", "_", law.lower()).strip("_")[:40],
    }


def contradict(tiles: dict[str, str], known_laws: list[str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    rule = tiles.get("RULE") or ""
    if rule in known_laws:
        issues.append({"id": "ALREADY_KNOWN", "severity": "INFO", "law": rule})
    printed = (tiles.get("FAILURE_CASE") or "") + (tiles.get("FACT") or "")
    if "PASS" in printed and "NE_" not in (tiles.get("INVARIANT") or ""):
        issues.append({"id": "PRINTED_PASS_RISK", "severity": "HIGH", "law": "PRINTED_PASS_NE_EVIDENCE"})
    return issues


def graph_from_tiles(tiles: dict[str, str], *, source_sha: str) -> dict[str, Any]:
    nodes = [{"id": key, "kind": "tile", "text": value} for key, value in tiles.items()]
    edges = [
        {"from": "FACT", "to": "RULE", "rel": "grounds"},
        {"from": "RULE", "to": "CASE", "rel": "becomes"},
        {"from": "RULE", "to": "INVARIANT", "rel": "stabilizes"},
        {"from": "EXAMPLE", "to": "COUNTEREXAMPLE", "rel": "negates"},
        {"from": "PROCEDURE", "to": "SKILL_CANDIDATE", "rel": "compiles"},
    ]
    return {
        "schema": "raios.kae-graph.v1",
        "second_wal": False,
        "lightrag": False,
        "source_sha": source_sha,
        "nodes": nodes,
        "edges": edges,
        "knowledge_state": "DISCOVERED",
    }


def verify_semantic_mutation(
    *,
    http_status: int,
    body: dict[str, Any] | None,
    entity_present_after: bool | None,
) -> dict[str, Any]:
    """Compiled skill candidate. DISCOVERED. Not CANONICAL. Not Main Cortex."""
    printed_ok = 200 <= int(http_status) < 300
    body = body if isinstance(body, dict) else {}
    semantic = body.get("success") is True
    if printed_ok and body.get("malformed"):
        return {
            "ok": False,
            "conclude": "REJECT_MALFORMED",
            "law": "HTTP_2XX_NE_SEMANTIC_SUCCESS",
            "skill": "verify_semantic_mutation",
        }
    if printed_ok and not semantic:
        return {
            "ok": False,
            "conclude": "REJECT_FALSE_POSITIVE",
            "law": "HTTP_2XX_NE_SEMANTIC_SUCCESS",
            "skill": "verify_semantic_mutation",
        }
    if semantic and entity_present_after is False:
        return {
            "ok": False,
            "conclude": "REJECT_MISSING_ENTITY",
            "law": "PRINTED_SUCCESS_NE_OBSERVED_STATE_CHANGE",
            "skill": "verify_semantic_mutation",
        }
    return {
        "ok": bool(printed_ok and semantic and entity_present_after is not False),
        "conclude": "PROVISIONAL_OK_NOT_CANONICAL",
        "law": "HTTP_2XX_NE_SEMANTIC_SUCCESS",
        "skill": "verify_semantic_mutation",
        "canonical": False,
    }


def case_factory(tiles: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "kind": "question",
            "prompt": tiles.get("QUIZ"),
            "expect": "REJECT_FALSE_POSITIVE",
        },
        {
            "kind": "attempt_surface",
            "prompt": tiles.get("EXAMPLE"),
            "fixture": {"http_status": 200, "body": {"success": False}, "entity_present_after": None},
        },
        {
            "kind": "counterexample",
            "prompt": tiles.get("COUNTEREXAMPLE"),
            "fixture": {"http_status": 201, "body": {"success": True}, "entity_present_after": False},
        },
        {
            "kind": "adversarial",
            "prompt": tiles.get("ADVERSARIAL_VARIANT"),
            "fixture": {"http_status": 200, "body": {"malformed": True}, "entity_present_after": None},
        },
    ]


def replay(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for case in cases:
        fixture = case.get("fixture")
        if not fixture:
            results.append({"kind": case.get("kind"), "ok": True, "note": "prompt_only"})
            continue
        verdict = verify_semantic_mutation(**fixture)
        expect_reject = case.get("kind") in {"attempt_surface", "counterexample", "adversarial"}
        ok = (verdict.get("ok") is False) if expect_reject else True
        results.append({"kind": case.get("kind"), "ok": ok, "verdict": verdict})
    reused = sum(1 for row in results if row.get("ok"))
    return {
        "results": results,
        "reused_on_unseen": reused,
        "cases": len(results),
        "replayed": True,
        "promoted": False,
    }


def tournament(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare already-authorized claims. Does not call C2/C3/C4. Not a vote for truth."""
    if any(str(c.get("source") or "").startswith("live-") for c in claims):
        return {"ok": False, "error": "THIS_CHANNEL_NO_C_SEAT_CONSULT", "consult_used": False}
    bag: dict[str, list[str]] = {}
    for claim in claims:
        source = str(claim.get("source") or "unknown")
        laws = LAW_RE.findall(str(claim.get("text") or ""))
        bag[source] = laws or [str(claim.get("text") or "")[:80]]
    sources = list(bag)
    agreement = []
    conflict = []
    if len(sources) >= 2:
        a, b = set(bag[sources[0]]), set(bag[sources[1]])
        agreement = sorted(a & b)
        if a and b and not (a & b):
            conflict.append({"a": sources[0], "b": sources[1], "a_laws": bag[sources[0]], "b_laws": bag[sources[1]]})
    return {
        "ok": True,
        "consult_used": False,
        "summoned": False,
        "vote_is_truth": False,
        "sources": sources,
        "agreement": agreement,
        "conflict": conflict,
        "law": "TEACHER_TOURNAMENT_NE_VOTE_NE_TRUTH",
    }


def yield_metrics(*, tiles: dict[str, str], external_calls: int, replayed_ok: int, ingested: int) -> dict[str, Any]:
    calls = max(int(external_calls), 0)
    tile_n = len([v for v in tiles.values() if v])
    knowledge_yield = round(tile_n / max(calls, 1), 4)
    efficiency = round(replayed_ok / max(int(ingested), 1), 4)
    return {
        "external_calls": calls,
        "tiles": tile_n,
        "knowledge_yield": knowledge_yield,
        "call_saved": calls == 0,
        "assimilation_efficiency": efficiency,
        "ingested": ingested,
        "reused_on_unseen": replayed_ok,
        "next_external_call_should_drop": True,
    }


def assimilate(
    text: str,
    *,
    source_kind: str = "authorized_text",
    source_path: str | None = None,
    external_calls: int = 0,
    known_laws: list[str] | None = None,
    ingest: bool = True,
) -> dict[str, Any]:
    adapted = source_adapter(source_kind, text, path=source_path)
    if not adapted.get("ok"):
        adapted.update({"schema": "raios.kae.v1", "gl005_proven": False, "canonical": False})
        return adapted
    atoms = extract_atoms(adapted["text"])
    tiles = retile(adapted["text"], atoms)
    issues = contradict(tiles, known_laws or list(LAWS))
    graph = graph_from_tiles(tiles, source_sha=adapted["sha256"])
    cases = case_factory(tiles)
    played = replay(cases)
    metrics = yield_metrics(
        tiles=tiles,
        external_calls=external_calls,
        replayed_ok=int(played.get("reused_on_unseen") or 0),
        ingested=1,
    )
    candidate = None
    if ingest:
        from pathlib import Path
        import sys

        root = Path(__file__).resolve()
        for parent in root.parents:
            if (parent / "scripts" / "ai-os" / "raios_learn_ingest.py").exists():
                sys.path.insert(0, str(parent / "scripts" / "ai-os"))
                break
        from raios_learn_ingest import ingest as ingest_fn

        candidate = ingest_fn(
            f"KAE {tiles.get('RULE')}: {tiles.get('FACT')}",
            f"kae:{source_kind}",
            [tiles.get("RULE") or "", tiles.get("INVARIANT") or ""],
        )
    return {
        "schema": "raios.kae.v1",
        "ok": True,
        "source": {k: adapted[k] for k in ("kind", "path", "sha256", "redacted") if k in adapted},
        "atoms": atoms,
        "tiles": tiles,
        "contradictions": issues,
        "graph": graph,
        "cases": cases,
        "replay": played,
        "metrics": metrics,
        "candidate": {"id": (candidate or {}).get("id"), "knowledge_state": "DISCOVERED"} if candidate else None,
        "cortex_used": False,
        "cortex_isolated": True,
        "consult_used": False,
        "summoned": False,
        "canonical": False,
        "promoted": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": list(LAWS),
    }
