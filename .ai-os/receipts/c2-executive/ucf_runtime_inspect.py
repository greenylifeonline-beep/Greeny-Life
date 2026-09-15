"""C5/MCP/CC inspect. No tokens printed. No process mutation."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life")
LOGS = Path.home() / ".raios" / "runtime" / "c5" / "logs"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url: str, timeout: int) -> dict:
    ts = utc()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(800).decode("utf-8", "replace")
            parsed = None
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            return {"ts": ts, "status": "OK", "http": resp.status, "url": url, "json": parsed, "body_prefix": body[:400]}
    except Exception as e:
        return {"ts": ts, "status": "FAIL", "error": type(e).__name__, "detail": str(e)[:300], "url": url}


def tasklist_pid(pid: int) -> str:
    try:
        return subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "LIST", "/V"],
            text=True,
            timeout=20,
        )
    except Exception as e:
        return f"TASKLIST_ERR {type(e).__name__} {e}"


def netstat_ports() -> str:
    try:
        raw = subprocess.check_output(["netstat", "-ano"], text=True, timeout=20)
        keep = []
        for line in raw.splitlines():
            if any(x in line for x in (":8766", ":8788", ":8770", ":8787")) and "LISTENING" in line.upper():
                keep.append(line.strip())
        return "\n".join(keep) or "NONE"
    except Exception as e:
        return f"NETSTAT_ERR {type(e).__name__} {e}"


def main() -> int:
    actor_ids = []
    token_path = ROOT / ".ai-os" / "mcp" / "tokens.local.json"
    if token_path.exists():
        data = json.loads(token_path.read_text(encoding="utf-8"))
        for row in data.get("actors") or []:
            actor_ids.append(str(row.get("actor_id") or ""))
    log_meta = []
    if LOGS.exists():
        for p in sorted(LOGS.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:12]:
            st = p.stat()
            log_meta.append({"name": p.name, "bytes": st.st_size, "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    report = {
        "schema": "raios.ucf.runtime-inspect.v1",
        "generated_at_utc": utc(),
        "token_actor_ids": actor_ids,
        "pid_17436_tasklist": tasklist_pid(17436),
        "pid_63464_tasklist": tasklist_pid(63464),
        "health": {
            "c5_root": http_get("http://127.0.0.1:8766/", 8),
            "c5_health": http_get("http://127.0.0.1:8766/health", 8),
            "mcp_health": http_get("http://127.0.0.1:8788/health", 8),
            "cc_health": http_get("http://127.0.0.1:8770/health", 8),
        },
        "c5_logs": log_meta,
        "listeners": netstat_ports(),
    }
    out = ROOT / ".ai-os" / "receipts" / "c2-executive" / "UCF-RUNTIME-INSPECT.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "written": str(out),
        "token_actor_ids": actor_ids,
        "c5_health": report["health"]["c5_health"].get("status"),
        "c5_root": report["health"]["c5_root"].get("status"),
        "mcp": report["health"]["mcp_health"].get("status"),
        "cc": report["health"]["cc_health"].get("status"),
        "c5_http": report["health"]["c5_health"].get("http"),
        "c5_error": report["health"]["c5_health"].get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
