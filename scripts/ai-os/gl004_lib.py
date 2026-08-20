#!/usr/bin/env python3
"""GL-004 shared contract: bind a live Next process. Never spawn. Never kill.

Laws (DISCOVERED, not CANONICAL):
  LIVE_PROCESS_CAN_SATISFY_RUNTIME_PROOF_IF_IDENTITY_AND_HTTP_EVIDENCE_ARE_BOUND
  BIND_EXISTING_NE_SPAWN
  DEV_LISTEN_NE_PRODUCTION_BUILD
  HTTP_200_ON_ROOT_NE_APP_HEALTH
  ISOLATED_BUILD_NE_SECOND_RUNTIME
  PARENT_SUCCESS_REQUIRES_ALL_REQUIRED_CHILDREN_SUCCESS
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ISOLATED_DIST = ".next-gl004-proof"
PRELOAD = Path(__file__).resolve().parent / "gl004-isolated-dist-preload.cjs"
REQUIRED_CHILDREN = (
    "TYPECHECK",
    "BUILD",
    "TEST_CANONICAL",
    "TEST_TASK_ORCHESTRATION",
    "RUNTIME_TRACE",
)

# Binder exits. 0 is the only success for RUNTIME_TRACE.
EXIT_BOUND = 0
EXIT_USAGE = 1
EXIT_NO_PROCESS = 2
EXIT_AMBIGUOUS = 3
EXIT_CWD_MISMATCH = 4
EXIT_NO_PORT = 5
EXIT_HTTP_INVALID = 6
EXIT_SPAWN_REFUSED = 7
EXIT_PLATFORM = 8


class BindError(RuntimeError):
    def __init__(self, code: int, reason: str, extra: dict[str, Any] | None = None):
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.extra = extra or {}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or r.stderr or "").strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def parent_exit(children: list[dict[str, Any]]) -> int:
    """0 only if every required child is present and exit==0. Missing = 2."""
    by_name = {c.get("name"): c for c in children}
    codes: list[int] = []
    for name in REQUIRED_CHILDREN:
        child = by_name.get(name)
        if child is None or child.get("exit") is None:
            codes.append(2)
            continue
        try:
            codes.append(int(child["exit"]))
        except (TypeError, ValueError):
            codes.append(2)
    if any(c != 0 for c in codes):
        return max(c for c in codes if c != 0)
    return 0


def gl004_proven(children: list[dict[str, Any]], parent: int) -> bool:
    return parent == 0 and parent_exit(children) == 0


def read_cmdline(pid: int) -> str:
    raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def read_comm(pid: int) -> str:
    return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8", errors="replace").strip()


def read_cwd(pid: int) -> Path:
    return Path(os.readlink(f"/proc/{pid}/cwd")).resolve()


def read_status(pid: int) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def read_environ(pid: int) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = Path(f"/proc/{pid}/environ").read_bytes()
    for item in raw.split(b"\x00"):
        if not item or b"=" not in item:
            continue
        k, v = item.split(b"=", 1)
        out[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    return out


def start_iso(pid: int) -> str:
    ticks = os.sysconf("SC_CLK_TCK")
    after = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace").rsplit(")", 1)[1].split()
    start_ticks = int(after[19])
    btime = 0
    for line in Path("/proc/stat").read_text(encoding="utf-8").splitlines():
        if line.startswith("btime "):
            btime = int(line.split()[1])
            break
    ts = btime + (start_ticks / float(ticks))
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def socket_inodes(pid: int) -> set[int]:
    found: set[int] = set()
    fd_dir = Path(f"/proc/{pid}/fd")
    for fd in fd_dir.iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith("socket:["):
            found.add(int(target[8:-1]))
    return found


def _ipv4(hexaddr: str) -> str:
    packed = struct.pack("<I", int(hexaddr, 16))
    return socket.inet_ntoa(packed)


def _ipv6(hexaddr: str) -> str:
    raw = bytes.fromhex(hexaddr)
    parts = b"".join(raw[i : i + 4][::-1] for i in range(0, 16, 4))
    return socket.inet_ntop(socket.AF_INET6, parts)


def parse_proc_net(path: Path, family: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 10:
            continue
        if parts[3] != "0A":
            continue
        local = parts[1]
        iphex, porthex = local.split(":")
        port = int(porthex, 16)
        inode = int(parts[9])
        ip = _ipv6(iphex) if family == "tcp6" else _ipv4(iphex)
        rows.append({"family": family, "ip": ip, "port": port, "inode": inode})
    return rows


def listening_ports(pid: int) -> list[dict[str, Any]]:
    inodes = socket_inodes(pid)
    rows = parse_proc_net(Path("/proc/net/tcp"), "tcp") + parse_proc_net(Path("/proc/net/tcp6"), "tcp6")
    return [r for r in rows if r["inode"] in inodes]


def http_probe(url: str, timeout: float = 8.0) -> dict[str, Any]:
    t0 = time.time()
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "gl004-runtime-bind"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(500)
            headers = {k: v for k, v in list(resp.headers.items())[:16]}
            return {
                "url": url,
                "status": int(resp.status),
                "headers": headers,
                "body_prefix": body.decode("utf-8", "replace"),
                "ms": int((time.time() - t0) * 1000),
            }
    except urllib.error.HTTPError as err:
        body = err.read(500)
        headers = {k: v for k, v in list(err.headers.items())[:16]} if err.headers else {}
        return {
            "url": url,
            "status": int(err.code),
            "headers": headers,
            "body_prefix": body.decode("utf-8", "replace"),
            "ms": int((time.time() - t0) * 1000),
        }
    except Exception as err:
        return {"url": url, "status": None, "error": str(err), "ms": int((time.time() - t0) * 1000)}


def next_identity_ok(probe: dict[str, Any]) -> bool:
    if probe.get("status") != 200:
        return False
    headers = {str(k).lower(): str(v).lower() for k, v in (probe.get("headers") or {}).items()}
    powered = headers.get("x-powered-by", "")
    body = str(probe.get("body_prefix") or "").lower()
    return "next" in powered or "next.js" in body or "/_next/" in body


def classify_mode(cmdline: str, environ: dict[str, str], ancestors: list[dict[str, Any]]) -> str:
    blob = " ".join([cmdline] + [a.get("cmdline", "") for a in ancestors] + list(environ.values()))
    if "__NEXT_DEV_SERVER=1" in environ or environ.get("__NEXT_DEV_SERVER") == "1":
        return "dev"
    if "next start" in blob:
        return "start"
    if "next dev" in blob or "npm run dev" in blob:
        return "dev"
    return "unknown"


def is_next_candidate(pid: int) -> bool:
    try:
        comm = read_comm(pid)
        cmd = read_cmdline(pid)
    except OSError:
        return False
    blob = f"{comm} {cmd}".lower()
    if "gl004" in blob:
        return False
    return "next-server" in blob or "next dev" in blob or "next start" in blob or "/.bin/next" in blob


def ancestors_of(pid: int, limit: int = 12) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    current = pid
    for _ in range(limit):
        if current in seen or current <= 1:
            break
        seen.add(current)
        try:
            st = read_status(current)
            cmd = read_cmdline(current)
            chain.append(
                {
                    "pid": current,
                    "ppid": int(st.get("PPid") or 0),
                    "name": st.get("Name"),
                    "cmdline": cmd,
                    "cwd": str(read_cwd(current)),
                    "start": start_iso(current),
                }
            )
            current = int(st.get("PPid") or 0)
        except OSError:
            break
    return chain


def discover_next_pids() -> list[int]:
    pids: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            if is_next_candidate(pid):
                pids.append(pid)
        except OSError:
            continue
    return sorted(pids)


def locate_log(chain: list[dict[str, Any]]) -> dict[str, Any]:
    start_log = Path("/tmp/cursor/start-user/start-user.log")
    blob = " ".join(a.get("cmdline", "") for a in chain)
    chosen: Path | None = None
    if "start-user.sh" in blob and start_log.exists():
        chosen = start_log
    elif start_log.exists():
        chosen = start_log
    tail = ""
    if chosen and chosen.exists():
        lines = chosen.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-40:])
    stdout_target = None
    try:
        stdout_target = os.readlink(f"/proc/{chain[0]['pid']}/fd/1")
    except OSError:
        pass
    return {
        "path": str(chosen) if chosen else None,
        "stdout_fd": stdout_target,
        "tail": tail,
    }


def bind_live(repo: Path | None = None) -> dict[str, Any]:
    if os.name == "nt":
        raise BindError(
            EXIT_PLATFORM,
            "USE_POWERSHELL_TWIN",
            {"twin": "scripts/ai-os/gl004-runtime-bind.ps1"},
        )
    repo = (repo or ROOT).resolve()
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    pids = discover_next_pids()
    matched: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for pid in pids:
        try:
            cwd = read_cwd(pid)
            cmd = read_cmdline(pid)
            comm = read_comm(pid)
            ports = listening_ports(pid)
        except OSError:
            continue
        rec = {"pid": pid, "cwd": str(cwd), "cmdline": cmd, "comm": comm, "ports": ports}
        if cwd == repo and ports:
            matched.append(rec)
        else:
            ignored.append(rec)

    listeners = [m for m in matched if m["ports"]]
    if not listeners:
        raise BindError(
            EXIT_NO_PROCESS,
            "NO_LIVE_NEXT_LISTENER_FOR_REPO",
            {"discovered": pids, "ignored": ignored, "head": head},
        )

    serverish = [
        m
        for m in listeners
        if "next-server" in (m.get("comm") or "").lower() or "next-server" in (m.get("cmdline") or "").lower()
    ]
    chosen_list = serverish or listeners
    if len(chosen_list) > 1:
        raise BindError(EXIT_AMBIGUOUS, "SECOND_RUNTIME_OR_AMBIGUOUS", {"candidates": chosen_list})

    chosen = chosen_list[0]
    pid = int(chosen["pid"])
    cwd = Path(chosen["cwd"])
    if cwd != repo:
        raise BindError(EXIT_CWD_MISMATCH, "CWD_NE_REPO", {"cwd": str(cwd), "repo": str(repo)})

    ports = chosen["ports"]
    if not ports:
        raise BindError(EXIT_NO_PORT, "NO_LISTEN_PORT", {"pid": pid})

    port = int(ports[0]["port"])
    chain = ancestors_of(pid)
    environ = {}
    try:
        environ = read_environ(pid)
    except OSError:
        pass
    mode = classify_mode(chosen["cmdline"], environ, chain)
    probes = [
        http_probe(f"http://127.0.0.1:{port}/"),
        http_probe(f"http://127.0.0.1:{port}/api/health"),
        http_probe(f"http://127.0.0.1:{port}/api/workflow"),
        http_probe(f"http://127.0.0.1:{port}/api/tasks"),
    ]
    root_probe = probes[0]
    if not next_identity_ok(root_probe):
        raise BindError(
            EXIT_HTTP_INVALID,
            "HTTP_IDENTITY_INVALID",
            {"pid": pid, "port": port, "probe": root_probe},
        )

    st = read_status(pid)
    log = locate_log(chain)
    return {
        "schema": "raios.gl004-runtime-bind.v1",
        "invariant": "LIVE_PROCESS_CAN_SATISFY_RUNTIME_PROOF_IF_IDENTITY_AND_HTTP_EVIDENCE_ARE_BOUND",
        "laws": [
            "BIND_EXISTING_NE_SPAWN",
            "DEV_LISTEN_NE_PRODUCTION_BUILD",
            "HTTP_200_ON_ROOT_NE_APP_HEALTH",
        ],
        "bound_at": utc(),
        "repo": str(repo),
        "head": head,
        "branch": branch,
        "pid": pid,
        "ppid": int(st.get("PPid") or 0),
        "comm": chosen["comm"],
        "cmdline": chosen["cmdline"],
        "cwd": str(cwd),
        "start": chain[0]["start"] if chain else None,
        "mode": mode,
        "node_env": environ.get("NODE_ENV"),
        "next_dev_server": environ.get("__NEXT_DEV_SERVER"),
        "ports": ports,
        "listen_port": port,
        "http": probes,
        "http_root_ok": True,
        "http_valid_means": "GET / == 200 and Next.js identity. Other routes are execution evidence, not health PASS.",
        "log": log,
        "ancestors": chain,
        "ignored_other_next": ignored,
        "spawned": False,
        "killed": False,
        "second_runtime": False,
    }


def refuse_spawn() -> None:
    raise BindError(EXIT_SPAWN_REFUSED, "SPAWN_REFUSED_BIND_EXISTING_NE_SPAWN")
