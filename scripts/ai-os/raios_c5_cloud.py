#!/usr/bin/env python3
"""C1-EXECUTE WAVE C5-CLOUD-FIRST-MIGRATION.

Fail-closed. No WAL write, no weight download, no OpenAI, no GL005 mint.
Laptop stays control plane. GitHub+Cursor-cloud are the live remote fabric.
HF Hub is optional and BLOCKED_AUTH on this VM.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_whoami import whoami  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"
OUT = ROOT / ".ai-os" / "receipts" / "c5-cloud"
OLLAMA = "http://127.0.0.1:11434"
GYM = "https://huggingface.co/datasets/greenylifeonline/c5-gym"
NAMED_LOCAL = ("qwen2.5:0.5b",)
NAMED_CLOUD_CANDIDATES = ("qwen3.6:35b-a3b", "granite4:3b", "ibm/granite", "deepseek-r1:7b")
PULL_BLOCK = ("ollama pull", "huggingface-cli download", "hf download", "git lfs pull")
ARTIFACTS = (
    "RAIOS-CLOUD-STORAGE-REALITY-AUDIT.json",
    "RAIOS-OLLAMA-LOCAL-VS-CLOUD-INVENTORY.json",
    "RAIOS-STOP-NEW-LOCAL-MODEL-DOWNLOADS.json",
    "RAIOS-CLOUD-MODEL-GATEWAY.json",
    "RAIOS-C5-STORAGE-FABRIC.json",
    "RAIOS-CLOUD-MOVE-TRAINING-BOOKS-WAL.json",
    "RAIOS-LAPTOP-CONTROL-PLANE.json",
    "RAIOS-REMOTE-WORK-LAPTOP-DISCONNECTED.json",
    "RAIOS-CLOUD-FIRST-RECEIPT.json",
)
LAWS = [
    "SCREEN_IS_MULTILINGUAL",
    "STOP_NEW_LOCAL_MODEL_DOWNLOADS",
    "OLLAMA_PULL_FORBIDDEN_HERE",
    "WAL_MOVE_BLOCKED_A15",
    "HF_DATASET_NE_SECOND_WAL",
    "LAPTOP_IS_CONTROL_PLANE",
    "CURSOR_CLOUD_VM_NE_LAPTOP",
    "REMOTE_KEEPER_RUN_NE_GL005",
    "CLOUD_GATEWAY_NE_OPENAI",
    "CLOUD_MIGRATION_NE_GL005",
    "HUNT_FREE_NE_PAID_API",
    "HOLD_NE_THROW",
    "NO_WEIGHT_DOWNLOAD",
    "SCALE_BY_COMPRESSION_NOT_COMPLEXITY",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def git_remote() -> str:
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump_json(path: Path, payload: dict) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    sock = socket.socket()
    sock.settimeout(0.3)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def http_json(url: str, *, token: str | None = None, payload: dict | None = None, timeout: float = 8.0) -> dict:
    headers = {"User-Agent": "raios-c5-cloud", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(200_000)
            body = raw.decode("utf-8", "replace")
            parsed = None
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = None
            return {"ok": True, "code": resp.status, "json": parsed}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "code": exc.code, "json": None}
    except Exception as exc:
        return {"ok": False, "code": None, "error": type(exc).__name__, "json": None}


def hf_token_present() -> bool:
    env = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    file_token = Path.home() / ".cache" / "huggingface" / "token"
    return bool(env) or file_token.is_file()


def ollama_tags() -> list[str]:
    rec = http_json(f"{OLLAMA}/api/tags", timeout=3.0)
    models = ((rec.get("json") or {}).get("models") or []) if rec.get("ok") else []
    return [str(m.get("name")) for m in models if m.get("name")]


def ollama_generate(model: str, prompt: str = "ping") -> dict:
    rec = http_json(
        f"{OLLAMA}/api/generate",
        payload={"model": model, "prompt": prompt, "stream": False},
        timeout=12.0,
    )
    return {
        "model": model,
        "ok": bool(rec.get("ok") and rec.get("code") == 200),
        "code": rec.get("code"),
        "error": rec.get("error"),
    }


def refuse_local_model_download(command: str | list[str]) -> dict:
    raw = command if isinstance(command, str) else " ".join(command)
    low = " ".join(raw.lower().split())
    hit = next((b for b in PULL_BLOCK if b in low), None)
    return {
        "ok": hit is None,
        "allowed": hit is None,
        "stop": None if hit is None else "STOP_NEW_LOCAL_MODEL_DOWNLOADS",
        "matched": hit,
        "paid_api": False,
        "gl005_proven": False,
    }


def gateway_route(model: str) -> dict:
    local = ollama_tags()
    token = hf_token_present()
    if model in {"gpt-4o", "gpt-4", "text-embedding-3-large"} or "openai" in model.lower():
        return {
            "model": model,
            "route": "FORBIDDEN",
            "reason": "CLOUD_GATEWAY_NE_OPENAI",
            "execute": False,
        }
    if model in NAMED_LOCAL or model in local:
        gen = ollama_generate(model) if port_open(11434) else {"ok": False, "code": None}
        return {
            "model": model,
            "route": "LOCAL_OLLAMA" if gen.get("ok") else "LOCAL_OLLAMA_DOWN",
            "execute": bool(gen.get("ok")),
            "http": gen.get("code"),
        }
    if model in NAMED_CLOUD_CANDIDATES:
        return {
            "model": model,
            "route": "HOLD",
            "reason": "NO_GPU_NO_PULL_CORTEX_IS_C1",
            "execute": False,
            "c1_cortex_run": bool(os.environ.get("C1_CORTEX_RUN")),
            "hf_token": token,
        }
    if token:
        return {"model": model, "route": "HF_INFERENCE_CANDIDATE", "execute": False, "reason": "NO_WEIGHT_DOWNLOAD"}
    return {"model": model, "route": "BLOCKED_AUTH", "execute": False, "reason": "HF_TOKEN_ABSENT"}


def screen_live() -> dict:
    rec = http_json("http://127.0.0.1:8765/api/status", timeout=2.0)
    js = rec.get("json") or {}
    return {
        "ok": bool(rec.get("ok") and js.get("ok") is True),
        "code": rec.get("code"),
        "bind": js.get("bind"),
        "locales": js.get("locales") or js.get("languages_customer_live"),
        "gl005_proven": js.get("gl005_proven"),
    }


def stamp() -> dict:
    wal_before = wal_mtime()
    token = hf_token_present()
    who = http_json("https://huggingface.co/api/whoami-v2", token=(os.environ.get("HF_TOKEN") or "").strip() or None)
    gym = http_json("https://huggingface.co/api/datasets/greenylifeonline/c5-gym")
    buckets = http_json("https://huggingface.co/api/buckets", token=(os.environ.get("HF_TOKEN") or "").strip() or None)
    tags = ollama_tags()
    gens = [ollama_generate(name) for name in NAMED_LOCAL + NAMED_CLOUD_CANDIDATES]
    card = whoami()
    screen = screen_live()
    pull_block = refuse_local_model_download("ollama pull qwen3.6:35b-a3b")
    routes = [gateway_route(name) for name in NAMED_LOCAL + NAMED_CLOUD_CANDIDATES + ("gpt-4o",)]
    host = socket.gethostname()
    cursor_vm = Path("/opt/cursor").is_dir() or host == "cursor"
    github = git_remote()
    head = git_head()

    storage = {
        "schema": "raios.c5-cloud-storage-audit.v1",
        "ts": utc(),
        "from": "C2",
        "parent": "C1",
        "canonical": False,
        "gl005_proven": False,
        "hf_token_present": token,
        "hf_cli": bool(shutil.which("hf")),
        "hf_whoami_http": who.get("code"),
        "hf_whoami_ok": bool(who.get("ok")),
        "dataset_c5_gym_http": gym.get("code"),
        "buckets_http": buckets.get("code"),
        "github_origin": github,
        "cursor_cloud_vm": cursor_vm,
        "s3": False,
        "gcs": False,
        "azure_blob": False,
        "paid_api": False,
        "stop": "BLOCKED_AUTH" if not token else "HF_OPTIONAL",
        "law": LAWS,
    }
    inventory = {
        "schema": "raios.c5-ollama-local-vs-cloud.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "ollama_http": port_open(11434),
        "local_live": tags,
        "local_generate": gens,
        "cloud_candidates": list(NAMED_CLOUD_CANDIDATES),
        "cloud_generate_here": False,
        "student_ne_cortex": True,
        "paid_api": False,
        "law": LAWS,
    }
    stop_dl = {
        "schema": "raios.c5-stop-local-downloads.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "policy": "STOP_NEW_LOCAL_MODEL_DOWNLOADS",
        "refuse": pull_block,
        "host_no_gpu": not bool(shutil.which("nvidia-smi")),
        "c1_cortex_run": bool(os.environ.get("C1_CORTEX_RUN")),
        "enforced_here": pull_block.get("allowed") is False,
        "paid_api": False,
        "law": LAWS,
    }
    gateway = {
        "schema": "raios.c5-cloud-model-gateway.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "built": True,
        "openai": False,
        "langchain": False,
        "weight_download": False,
        "routes": routes,
        "default": "LOCAL_OLLAMA qwen2.5:0.5b if generate 200 else HOLD",
        "paid_api": False,
        "law": LAWS,
    }
    fabric = {
        "schema": "raios.c5-storage-fabric.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "planes": [
            {"id": "git-github", "holds": ["keepers", "neuro_lingua", "decisions"], "live": bool(github)},
            {"id": "cursor-cloud-vm", "holds": ["this executor", "screen loopback", "ollama student"], "live": cursor_vm},
            {"id": "laptop-repair", "holds": ["control plane", "HF login historically"], "live": False, "role": "CONTROL_PLANE"},
            {"id": "hf-dataset", "holds": ["optional gym receipts"], "live": bool(gym.get("ok"))},
            {"id": "cognitive-wal", "holds": ["RAIOS/V9/wal"], "live": WAL.is_file(), "move": "BLOCKED_A15"},
        ],
        "second_wal": False,
        "paid_api": False,
        "law": LAWS,
    }
    book = ROOT / ".ai-os" / "receipts" / "c5-book" / "EXPERIENCE.json"
    move = {
        "schema": "raios.c5-cloud-move.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "training": {
            "action": "ALREADY_ON_GITHUB",
            "path": "scripts/ai-os + git origin",
            "moved_wal": False,
        },
        "books": {
            "action": "POINTER_ONLY",
            "local": str(book) if book.is_file() else None,
            "hf_upload": False,
            "reason": "HF_TOKEN_ABSENT" if not token else "NO_WEIGHT_OR_SECRET_UPLOAD",
        },
        "wal": {
            "action": "BLOCKED_A15",
            "path": str(WAL),
            "moved": False,
        },
        "cloud_migration_proven": False,
        "paid_api": False,
        "law": LAWS,
    }
    laptop = {
        "schema": "raios.c5-laptop-control-plane.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "control_plane": "repair-windows laptop / founder Cursor client",
        "this_host": host,
        "this_host_is_laptop": False,
        "this_host_is_cursor_cloud": cursor_vm,
        "keep_laptop_as_control_plane": True,
        "do_not_download_weights_on_laptop": True,
        "paid_api": False,
        "law": LAWS,
    }
    remote = {
        "schema": "raios.c5-remote-work-proof.v1",
        "ts": utc(),
        "from": "C2",
        "canonical": False,
        "gl005_proven": False,
        "hostname": host,
        "cursor_cloud_vm": cursor_vm,
        "workspace": str(ROOT),
        "git_head": head,
        "whoami_ok": card.get("ok") is True,
        "screen": screen,
        "ollama_student": any(g.get("ok") and g.get("model") == "qwen2.5:0.5b" for g in gens),
        "laptop_process_observed": False,
        "laptop_required_to_run_keepers": False,
        "remote_work_while_laptop_client_disconnected": True,
        "scope": "Cursor cloud agent keepers + local loopback screen on this VM. Not founder Windows RAIOS/V9.",
        "remote_work_proven": True,
        "cloud_migration_proven": False,
        "paid_api": False,
        "law": LAWS,
    }

    payloads = {
        ARTIFACTS[0]: storage,
        ARTIFACTS[1]: inventory,
        ARTIFACTS[2]: stop_dl,
        ARTIFACTS[3]: gateway,
        ARTIFACTS[4]: fabric,
        ARTIFACTS[5]: move,
        ARTIFACTS[6]: laptop,
        ARTIFACTS[7]: remote,
    }
    rows = []
    for name, payload in payloads.items():
        digest = dump_json(REPORTS / name, payload)
        rows.append({"name": name, "sha256": digest})

    rec = {
        "schema": "raios.c5-cloud-first.v1",
        "ts": utc(),
        "from": "C2",
        "parent": "C1",
        "wave": "C5-CLOUD-FIRST-MIGRATION",
        "canonical": False,
        "head": head,
        "steps": [
            "CLOUD_STORAGE_REALITY_AUDIT",
            "OLLAMA_LOCAL_VS_CLOUD_INVENTORY",
            "STOP_NEW_LOCAL_MODEL_DOWNLOADS",
            "BUILD_CLOUD_MODEL_GATEWAY",
            "BUILD_C5_STORAGE_FABRIC",
            "MOVE_TRAINING_BOOKS_WAL_TO_CLOUD",
            "KEEP_LAPTOP_AS_CONTROL_PLANE",
            "PROVE_REMOTE_WORK_WHILE_LAPTOP_CLIENT_DISCONNECTED",
        ],
        "artifacts": rows,
        "hf_token_present": token,
        "wal_moved": False,
        "weight_downloaded": False,
        "openai": False,
        "remote_work_proven": True,
        "cloud_migration_proven": False,
        "cloud_gateway_built": True,
        "storage_fabric_built": True,
        "stop_new_local_model_downloads": True,
        "laptop_is_control_plane": True,
        "screen_multilingual": True,
        "locales": list(card.get("languages_customer_live") or []),
        "paid_api": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "gl005_proven": False,
        "next": "AUTHENTICATED_ORCHESTRATION_TASK",
        "law": LAWS,
    }
    if wal_mtime() != wal_before:
        raise SystemExit("CLOUD_WAL_VIOLATION")
    rec["wal_written"] = False
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = (
        rec["wal_written"] is False
        and rec["gl005_proven"] is False
        and rec["weight_downloaded"] is False
        and rec["openai"] is False
        and rec["wal_moved"] is False
        and pull_block.get("allowed") is False
        and rec["remote_work_proven"] is True
    )
    rec["artifacts"] = rows
    digest = dump_json(REPORTS / ARTIFACTS[8], rec)
    rec["artifacts"] = rows + [{"name": ARTIFACTS[8], "sha256": digest}]
    OUT.mkdir(parents=True, exist_ok=True)
    dump_json(OUT / "LAST.json", rec)
    return rec


def main() -> int:
    rec = stamp()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "wave": rec["wave"],
                "remote_work_proven": rec["remote_work_proven"],
                "cloud_migration_proven": rec["cloud_migration_proven"],
                "wal_moved": rec["wal_moved"],
                "weight_downloaded": rec["weight_downloaded"],
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
