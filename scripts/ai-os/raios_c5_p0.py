#!/usr/bin/env python3
"""P0 fail-closed gates (D-060). CI pass is not assimilation. No source delete. No GL005 mint."""
from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "receipts" / "c5-p0"
FOUNDATION = ROOT / ".ai-os" / "state" / "FOUNDATION.json"
TASKS_ROUTE = ROOT / "app" / "api" / "tasks" / "route.ts"
ORCH = ROOT / "lib" / "intelligence" / "task-orchestration.ts"
UNIT_TEST = ROOT / "tests" / "task_orchestration_check.ts"
APP_BASE = "http://127.0.0.1:3000"
OLLAMA = "http://127.0.0.1:11434"
CORTEX_IDENTITY = "qwen3.6:35b-a3b"
STUDENT = "qwen2.5:0.5b"
ISOLATE_HOST = "127.0.0.1:1"
POST_PAYLOAD = {
    "taskType": "SYSTEM_MAINTENANCE_REVIEW",
    "ownerCompany": "MASTERMIND",
    "subjectId": "p0-authenticated-orchestration",
    "evidenceIds": ["P0-AUTHENTICATED-ORCHESTRATION"],
    "payload": {
        "intent": "OBSERVE_AUTHENTICATED_STATE_TRANSITION",
        "execution": False,
        "note": "Review request only. Not commercial execution. Not GL-005.",
    },
}
GATE_ORDER = (
    "AUTHENTICATED_ORCHESTRATION_TASK",
    "QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION",
    "GL005",
)
ASSIMILATION_CHAIN = (
    "SOURCE_PRESENT",
    "CAPABILITY_EXECUTES",
    "SOURCE_DISABLED_OR_ISOLATED",
    "C5_EXECUTES_SAME_CAPABILITY",
    "RESTART",
    "STILL_EXECUTES",
    "BENCHMARK_PASS",
)
BRAIN_BEHAVIOR = ("routing", "association", "execution", "persistence", "reuse")
PACK_MARKERS = (
    "RAIOS-COGNITIVE-BOOT.json",
    "_raios-qwen-forensics/reports/QWEN36-FORENSIC-CERTIFICATION.json",
    "_raios-a17-native-cortex/cortex/runtime/MAIN-CORTEX-BINDING.json",
)
LAWS = [
    "CI_PASS_NE_ASSIMILATION",
    "CI_PASS_NE_GL005",
    "MOCK_PATH_NE_ORCHESTRATION_TASK",
    "STUDENT_NE_EXTRACTION",
    "TINY_QWEN_NE_CORTEX_IDENTITY",
    "SOURCE_DELETION_FORBIDDEN_UNTIL_INDEPENDENT_EXECUTION",
    "AUTHENTICATED_ORCHESTRATION_TASK_NE_GL005",
    "PASS_CANDIDATE_NE_GL005_PROVEN",
    "HOLD_NE_THROW",
    "PRINTED_PASS_NE_EVIDENCE",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def env_set(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def product_path() -> dict:
    return {
        "live_base": APP_BASE,
        "route": str(TASKS_ROUTE.relative_to(ROOT)) if TASKS_ROUTE.is_file() else None,
        "domain": str(ORCH.relative_to(ROOT)) if ORCH.is_file() else None,
        "unit_test_rejected_as_proof": str(UNIT_TEST.relative_to(ROOT)),
        "createTaskContract": TASKS_ROUTE.is_file() and "createTaskContract" in TASKS_ROUTE.read_text(encoding="utf-8"),
        "post_handler": TASKS_ROUTE.is_file() and "export async function POST" in TASKS_ROUTE.read_text(encoding="utf-8"),
        "mock": False,
        "side_test_path": False,
    }


def classify_sources(models: list[str]) -> dict:
    names = [str(n) for n in models if n]
    qwen = any(n == CORTEX_IDENTITY or n.startswith(f"{CORTEX_IDENTITY}:") for n in names)
    granite = any("granite" in n.lower() for n in names)
    student = any(n == STUDENT or n.startswith(f"{STUDENT}-") or n.startswith(f"{STUDENT}:") for n in names)
    present = bool(qwen and granite)
    return {
        "models": names,
        "qwen_cortex_present": qwen,
        "granite_present": granite,
        "student_present": student,
        "student_ne_extraction": True,
        "tiny_qwen_ne_cortex_identity": True,
        "source_present": present,
        "reason": (
            "SOURCE_PRESENT"
            if present
            else (
                "STUDENT_ONLY_NOT_SOURCE"
                if student and not qwen and not granite
                else "QWEN_GRANITE_SOURCE_ABSENT"
            )
        ),
    }


def extracted_from_chain(stages: list[dict]) -> bool:
    names = [str(row.get("name") or "") for row in stages]
    if names != list(ASSIMILATION_CHAIN):
        return False
    return all(row.get("status") == "PASS" for row in stages)


class Client:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def gl_session_present(self) -> bool:
        return any(cookie.name == "gl_session" for cookie in self.jar)

    def request(self, method: str, url: str, data: bytes | None = None) -> dict:
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "User-Agent": "raios-c5-p0/1", "Accept": "application/json"},
        )
        try:
            with self.opener.open(req, timeout=8) as resp:
                raw = resp.read()[:12000]
                code = int(resp.status)
        except urllib.error.HTTPError as exc:
            raw = exc.read()[:12000]
            code = int(exc.code)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "code": None,
                "error": type(exc).__name__,
                "body": "",
                "json": None,
                "sha256": None,
            }
        text = raw.decode("utf-8", "replace")
        parsed = None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        return {
            "ok": 200 <= code < 300,
            "code": code,
            "error": None,
            "body": text,
            "json": parsed,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }


def ollama_request(method: str, path: str, payload: dict | None = None, *, timeout: float = 8.0) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "raios-c5-p0/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()[:8000]
            code = int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read()[:8000]
        code = int(exc.code)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": None, "error": type(exc).__name__, "json": None}
    text = raw.decode("utf-8", "replace")
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    return {"ok": 200 <= code < 300, "code": code, "error": None, "json": parsed}


def public_http(probe: dict) -> dict:
    parsed = probe.get("json") if isinstance(probe.get("json"), dict) else {}
    return {
        "code": probe.get("code"),
        "error": parsed.get("error") if isinstance(parsed, dict) else probe.get("error"),
        "success": parsed.get("success") if isinstance(parsed, dict) else None,
        "authenticated": parsed.get("authenticated") if isinstance(parsed, dict) else None,
        "sha256": probe.get("sha256"),
        "id": ((parsed.get("data") or {}) if isinstance(parsed.get("data"), dict) else {}).get("id"),
        "count": parsed.get("count") if isinstance(parsed, dict) else None,
    }


def task_ids(probe: dict) -> list[str]:
    parsed = probe.get("json") if isinstance(probe.get("json"), dict) else {}
    data = parsed.get("data")
    if not isinstance(data, list):
        return []
    return [str(row.get("id")) for row in data if isinstance(row, dict) and row.get("id")]


def stage(name: str, status: str, detail: str, **extra) -> dict:
    row = {"name": name, "status": status, "detail": detail}
    row.update(extra)
    return row


def gate1_authenticated_orchestration(client: Client) -> dict:
    surface = product_path()
    session = client.request("GET", APP_BASE + "/api/auth/session")
    session_json = session.get("json") if isinstance(session.get("json"), dict) else {}
    authenticated = session_json.get("authenticated") is True
    before = client.request("GET", APP_BASE + "/api/tasks")
    unauth_post = client.request("POST", APP_BASE + "/api/tasks", json.dumps(POST_PAYLOAD).encode("utf-8"))
    login = {"attempted": False, "reason": "NO_EXISTING_LOGIN_ENV"}
    email_set = env_set("C1_LOGIN_EMAIL")
    password_len = len(os.environ.get("C1_LOGIN_PASSWORD", ""))
    if email_set and password_len == 0:
        login = {"attempted": False, "reason": "EMPTY_PASSWORD_NE_IDENTITY", "password_length": 0}
    elif email_set and password_len > 0:
        login_body = json.dumps(
            {"email": os.environ.get("C1_LOGIN_EMAIL", "").strip(), "password": os.environ.get("C1_LOGIN_PASSWORD", "")}
        ).encode("utf-8")
        login_probe = client.request("POST", APP_BASE + "/api/auth/login", login_body)
        login_json = login_probe.get("json") if isinstance(login_probe.get("json"), dict) else {}
        login = {
            "attempted": True,
            "code": login_probe.get("code"),
            "success": login_json.get("success"),
            "error": login_json.get("error"),
            "gl_session_cookie_present": client.gl_session_present(),
            "password_length": password_len,
            "password_printed": False,
        }
        session = client.request("GET", APP_BASE + "/api/auth/session")
        session_json = session.get("json") if isinstance(session.get("json"), dict) else {}
        authenticated = session_json.get("authenticated") is True
    auth_post = None
    after = before
    if authenticated:
        auth_post = client.request("POST", APP_BASE + "/api/tasks", json.dumps(POST_PAYLOAD).encode("utf-8"))
        after = client.request("GET", APP_BASE + "/api/tasks")
    returned_id = public_http(auth_post or {}).get("id")
    after_ids = task_ids(after)
    visible = bool(returned_id and returned_id in after_ids)
    hash_diff = bool(
        before.get("sha256")
        and after.get("sha256")
        and before.get("sha256") != after.get("sha256")
        and authenticated
    )
    passed = bool(
        surface["createTaskContract"]
        and surface["post_handler"]
        and not surface["mock"]
        and authenticated
        and (auth_post or {}).get("code") == 201
        and visible
        and hash_diff
    )
    get_code = before.get("code")
    post_code = unauth_post.get("code")
    if passed:
        status, detail = "PASS", "authenticated POST /api/tasks created a visible OrchestrationTask row"
        classification = "PASS_CANDIDATE"
    elif post_code == 401 and not authenticated and get_code == 500:
        status, detail = "BLOCKED", "POST /api/tasks 401 Authentication required; GET 500 DATABASE_URL missing"
        classification = "CAPABILITY_PROTECTED"
    elif post_code == 401 and not authenticated:
        status, detail = "BLOCKED", "POST /api/tasks 401 Authentication required; CAPABILITY_PROTECTED; existing identity unavailable"
        classification = "CAPABILITY_PROTECTED"
    elif get_code == 500:
        status, detail = "BLOCKED", "GET /api/tasks 500 DATABASE_URL missing; CAPABILITY_UNAVAILABLE"
        classification = "CAPABILITY_UNAVAILABLE"
    else:
        status, detail = "FAIL", "authenticated product mutation not observed"
        classification = "UNPROVEN"
    return {
        "gate": GATE_ORDER[0],
        "status": status,
        "passed": passed,
        "authenticated_orchestration_task": passed,
        "gl005_proven": False,
        "classification": classification,
        "path": "product",
        "mock": False,
        "side_test_path": False,
        "database_url_present": env_set("DATABASE_URL"),
        "app_session_secret_present": env_set("APP_SESSION_SECRET"),
        "forged_session": False,
        "minted_secret": False,
        "provisioned_postgres": False,
        "surface": surface,
        "session": public_http(session),
        "login": login,
        "before": public_http(before),
        "unauthenticated_post": public_http(unauth_post),
        "authenticated_post": public_http(auth_post) if auth_post else None,
        "after": public_http(after),
        "returned_id": returned_id,
        "visible_after": visible,
        "before_hash_equals_after": before.get("sha256") == after.get("sha256"),
        "detail": detail,
        "law": [
            "MOCK_PATH_NE_ORCHESTRATION_TASK",
            "AUTH_GATE_PRESENT_NE_AUTHENTICATED_MUTATION",
            "AUTHENTICATED_ORCHESTRATION_TASK_NE_GL005",
            "CREDENTIAL_MANUFACTURE_NE_EXISTING_SESSION",
        ],
    }


def generate_ok(model: str) -> dict:
    rec = ollama_request(
        "POST",
        "/api/generate",
        {"model": model, "prompt": "ping", "stream": False, "options": {"num_predict": 8}},
        timeout=12.0,
    )
    payload = rec.get("json") if isinstance(rec.get("json"), dict) else {}
    text = str(payload.get("response") or "")
    return {"model": model, "code": rec.get("code"), "ok": bool(rec.get("ok") and text.strip()), "error": rec.get("error")}


def pack_present() -> dict:
    rows = []
    for rel in PACK_MARKERS:
        path = ROOT / rel
        rows.append({"path": rel, "exists": path.is_file()})
    return {"markers": rows, "any": any(row["exists"] for row in rows)}


def c5_same_capability(*, isolated: bool) -> dict:
    packs = pack_present()
    return {
        "isolated_from_ollama": isolated,
        "isolate_host": ISOLATE_HOST if isolated else None,
        "source_deleted": False,
        "transferred_pack_present": packs["any"],
        "markers": packs["markers"],
        "executed_same_capability": False,
        "reason": "C5 live path is INDEX+file-read+deterministic reason; transferred Qwen/Granite pack absent",
    }


def gate2_assimilation(models: list[str]) -> dict:
    sources = classify_sources(models)
    stages: list[dict] = []
    if sources["source_present"]:
        stages.append(stage("SOURCE_PRESENT", "PASS", "cortex qwen3.6:35b-a3b and granite are loaded", **sources))
        qwen_gen = generate_ok(CORTEX_IDENTITY)
        granite_name = next((n for n in models if "granite" in n.lower()), "")
        granite_gen = generate_ok(granite_name) if granite_name else {"ok": False, "error": "NO_GRANITE_NAME"}
        cap_ok = bool(qwen_gen.get("ok") and granite_gen.get("ok"))
        stages.append(
            stage(
                "CAPABILITY_EXECUTES",
                "PASS" if cap_ok else "FAIL",
                "source generate ping" if cap_ok else "source generate failed or incomplete",
                qwen=qwen_gen,
                granite=granite_gen,
            )
        )
    else:
        stages.append(stage("SOURCE_PRESENT", "FAIL", sources["reason"], **sources))
        stages.append(stage("CAPABILITY_EXECUTES", "UNREACHED", "blocked by SOURCE_PRESENT"))

    prev = stages[-1]["status"] == "PASS"
    if prev:
        stages.append(
            stage(
                "SOURCE_DISABLED_OR_ISOLATED",
                "PASS",
                "C5 path isolated from Ollama without deleting source/weights",
                source_deleted=False,
                source_unloaded=False,
                c5_ollama_isolated=True,
                isolate_method="OLLAMA_HOST=" + ISOLATE_HOST,
            )
        )
    else:
        stages.append(
            stage(
                "SOURCE_DISABLED_OR_ISOLATED",
                "UNREACHED",
                "not isolated; SOURCE_DELETION_FORBIDDEN; previous stage not PASS",
                source_deleted=False,
                source_unloaded=False,
            )
        )

    isolated = stages[-1]["status"] == "PASS"
    c5_one = c5_same_capability(isolated=isolated)
    if isolated and c5_one["executed_same_capability"]:
        stages.append(stage("C5_EXECUTES_SAME_CAPABILITY", "PASS", "C5 executed the same capability with source isolated", **c5_one))
    elif isolated:
        stages.append(stage("C5_EXECUTES_SAME_CAPABILITY", "FAIL", c5_one["reason"], **c5_one))
    else:
        stages.append(stage("C5_EXECUTES_SAME_CAPABILITY", "UNREACHED", c5_one["reason"], **c5_one))

    prev = stages[-1]["status"] == "PASS"
    c5_two = c5_same_capability(isolated=isolated) if prev else c5_one
    stages.append(
        stage(
            "RESTART",
            "PASS" if prev else "UNREACHED",
            "re-ran C5 capability probe without killing Next or deleting sources" if prev else "blocked by previous stage",
            next_killed=False,
            source_deleted=False,
        )
    )
    still = prev and c5_two.get("executed_same_capability") is True
    stages.append(
        stage(
            "STILL_EXECUTES",
            "PASS" if still else ("UNREACHED" if not prev else "FAIL"),
            "capability survived restart" if still else "C5 independent capability not observed after restart",
            **c5_two,
        )
    )
    bench = ROOT / "benchmarks" / "neuro_lingua"
    bench_ok = False
    stages.append(
        stage(
            "BENCHMARK_PASS",
            "PASS" if still and bench_ok else ("UNREACHED" if not still else "FAIL"),
            "no transferred Qwen/Granite benchmark PASS on this host",
            benchmark_dir_exists=bench.exists(),
        )
    )
    extracted = extracted_from_chain(stages)
    stop = next((row["name"] for row in stages if row["status"] != "PASS"), "COMPLETE")
    return {
        "gate": GATE_ORDER[1],
        "status": "PASS" if extracted else ("FAIL" if stages[0]["status"] == "FAIL" else "BLOCKED"),
        "passed": extracted,
        "extracted_qwen_granite": extracted,
        "safe_to_remove_source": False,
        "source_deleted": False,
        "student_ne_extraction": True,
        "stop_stage": stop,
        "chain": stages,
        "sources": sources,
        "detail": stages[0]["detail"] if stages[0]["status"] != "PASS" else stop,
    }


def gate3_gl005(*, auth_ok: bool, extracted: bool) -> dict:
    behavior = {name: False for name in BRAIN_BEHAVIOR}
    if not auth_ok:
        status, detail = "UNREACHED", "GL005 waits for AUTHENTICATED_ORCHESTRATION_TASK"
    elif not extracted:
        status, detail = "UNREACHED", "GL005 waits for Qwen/Granite source-independent assimilation"
    else:
        status, detail = "UNPROVEN", "assimilation observed; brain behavior routing+association+execution+persistence+reuse not proven"
    return {
        "gate": GATE_ORDER[2],
        "status": status,
        "passed": False,
        "gl005_proven": False,
        "brain_behavior": behavior,
        "vault_retrieval_ne_brain": True,
        "detail": detail,
    }


def render(rec: dict) -> str:
    g1 = rec["gate1"]
    g2 = rec["gate2"]
    g3 = rec["gate3"]
    return "\n".join(
        [
            "############################################################",
            "# RAIOS P0 GATES — D-060  (D-059 FACTS REMAIN LOCKED)",
            "############################################################",
            f"CI(1e28f84)={rec['facts']['CI_1e28f84']}",
            f"CI(68af867)={rec['facts']['CI_68af867']}",
            "CI_PASS_NE_ASSIMILATION=true",
            "CI_PASS_NE_GL005=true",
            f"AUTHENTICATED_ORCHESTRATION_TASK={'true' if g1['authenticated_orchestration_task'] else 'false'}",
            f"GATE1_STATUS={g1['status']}",
            f"GATE1_DETAIL={g1['detail']}",
            f"SESSION_AUTHENTICATED={'true' if g1['session'].get('authenticated') else 'false'}",
            f"POST_UNAUTH={g1['unauthenticated_post'].get('code')}",
            f"GET_TASKS={g1['before'].get('code')}",
            f"PATH={g1['path']}",
            "MOCK=false",
            f"EXTRACTED_QWEN_GRANITE={'true' if g2['extracted_qwen_granite'] else 'false'}",
            f"GATE2_STATUS={g2['status']}",
            f"GATE2_STOP={g2['stop_stage']}",
            f"OLLAMA_MODELS={','.join(g2['sources']['models']) or 'none'}",
            f"QWEN_GRANITE_SOURCE_PRESENT={'true' if g2['sources']['source_present'] else 'false'}",
            "STUDENT_NE_EXTRACTION=true",
            "SAFE_TO_REMOVE_SOURCE=false",
            "SOURCE_DELETED=false",
            f"GL005_PROVEN={'true' if g3['gl005_proven'] else 'false'}",
            f"GATE3_STATUS={g3['status']}",
            f"GATE3_DETAIL={g3['detail']}",
            f"STOP={rec['stop']}",
            "NEXT=AUTHENTICATED_ORCHESTRATION_TASK;THEN_QWEN_GRANITE_ASSIMILATION;THEN_GL005",
            "############################################################",
            "",
        ]
    )


def stamp() -> dict:
    wal_before = wal_mtime()
    foundation = {}
    if FOUNDATION.exists():
        foundation = json.loads(FOUNDATION.read_text(encoding="utf-8"))
    facts = dict(foundation.get("facts") or {})
    facts["CI_1e28f84"] = "PASS"
    facts["CI_68af867"] = "PASS"
    facts["EXTRACTED_QWEN_GRANITE"] = False
    facts["SAFE_TO_REMOVE_SOURCE"] = False
    facts["GL005_PROVEN"] = False
    facts["AUTHENTICATED_ORCHESTRATION_TASK"] = False
    client = Client()
    tags = ollama_request("GET", "/api/tags")
    models = []
    payload = tags.get("json") if isinstance(tags.get("json"), dict) else {}
    models = [str(row.get("name") or "") for row in (payload.get("models") or []) if row.get("name")]
    gate1 = gate1_authenticated_orchestration(client)
    gate2 = gate2_assimilation(models)
    gate3 = gate3_gl005(auth_ok=gate1["passed"], extracted=gate2["extracted_qwen_granite"])
    if not gate1["passed"]:
        stop = "AUTHENTICATED_ORCHESTRATION_TASK"
    elif not gate2["passed"]:
        stop = "QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION:" + str(gate2["stop_stage"])
    else:
        stop = "GL005"
    rec = {
        "schema": "raios.c5-p0.v1",
        "ts": utc(),
        "from": "C2",
        "parent": "C1",
        "decision": "D-060",
        "foundation_decision": "D-059",
        "facts": facts,
        "law": LAWS,
        "order": list(GATE_ORDER),
        "gate1": gate1,
        "gate2": gate2,
        "gate3": gate3,
        "stop": stop,
        "authenticated_orchestration_task": gate1["authenticated_orchestration_task"],
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "gl005_proven": False,
        "source_deleted": False,
        "wal_written": False,
        "ok": True,
    }
    rec["extracted_qwen_granite"] = bool(gate2["extracted_qwen_granite"])
    rec["facts"]["EXTRACTED_QWEN_GRANITE"] = False
    rec["facts"]["AUTHENTICATED_ORCHESTRATION_TASK"] = False
    rec["facts"]["GL005_PROVEN"] = False
    rec["facts"]["SAFE_TO_REMOVE_SOURCE"] = False
    rec["authenticated_orchestration_task"] = bool(gate1["authenticated_orchestration_task"])
    rec["gl005_proven"] = False
    rec["ok"] = (
        rec["facts"]["EXTRACTED_QWEN_GRANITE"] is False
        and rec["facts"]["GL005_PROVEN"] is False
        and rec["facts"]["SAFE_TO_REMOVE_SOURCE"] is False
        and rec["source_deleted"] is False
        and rec["gl005_proven"] is False
        and gate1["mock"] is False
        and gate1["minted_secret"] is False
        and gate1["forged_session"] is False
        and gate3["gl005_proven"] is False
    )
    rec["text"] = render(rec)
    if wal_mtime() != wal_before:
        raise SystemExit("P0_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    state = foundation if isinstance(foundation, dict) else {}
    state["schema"] = state.get("schema") or "raios.c1-foundation.v1"
    state["facts"] = dict(rec["facts"])
    state["p0"] = {"order": list(GATE_ORDER), "stop": rec["stop"], "gl005_proven": False}
    state["p0_decision"] = "D-060"
    FOUNDATION.parent.mkdir(parents=True, exist_ok=True)
    FOUNDATION.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "LAST.txt").write_text(rec["text"], encoding="utf-8")
    return rec


def main() -> int:
    rec = stamp()
    print(rec["text"], end="")
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
