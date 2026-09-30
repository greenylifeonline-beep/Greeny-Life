"""RAIOS Remote Capability provider backed by the owned Desktop Commander local MCP.

This module never uses Desktop Commander Remote/hosted transport. It starts the
owned local MCP server over stdio, performs an MCP handshake, and exposes only
policy-allowlisted tools to the Universal MCP gateway.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any


class DesktopCommanderProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class DesktopCommanderProvider:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = dict(config or {})
        self.node = os.getenv("RAIOS_DCR_NODE") or str(
            self.config.get("node")
            or r"C:\Program Files\nodejs\node.exe"
        )
        self.entry = os.getenv("RAIOS_DCR_ENTRY") or str(
            self.config.get("entry")
            or r"C:\Users\Ghanam\.raios\runtime\providers\desktop-commander\source\candidate-20260927-175803\dist\index.js"
        )
        self.timeout_seconds = float(self.config.get("timeout_seconds") or 30)
        self.max_result_chars = int(self.config.get("max_result_chars") or 20000)
        self.read_tools = set(self.config.get("read_tools") or ())
        self.write_tools = set(self.config.get("write_tools") or ())
        self._proc: subprocess.Popen[bytes] | None = None
        self._messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stderr: deque[str] = deque(maxlen=80)
        self._lock = threading.RLock()
        self._request_id = 0
        self._tool_names: set[str] = set()

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _reader_loop(self, proc: subprocess.Popen[bytes]) -> None:
        stream = proc.stdout
        if stream is None:
            return
        while True:
            first = stream.readline()
            if not first:
                return
            raw = first.strip()
            if not raw:
                continue
            try:
                if raw.lower().startswith(b"content-length:"):
                    length = int(raw.split(b":", 1)[1].strip())
                    while True:
                        header = stream.readline()
                        if not header or header in {b"\r\n", b"\n"}:
                            break
                    payload = stream.read(length)
                    msg = json.loads(payload.decode("utf-8"))
                else:
                    msg = json.loads(raw.decode("utf-8"))
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(msg, dict):
                self._messages.put(msg)

    def _stderr_loop(self, proc: subprocess.Popen[bytes]) -> None:
        stream = proc.stderr
        if stream is None:
            return
        while True:
            line = stream.readline()
            if not line:
                return
            self._stderr.append(line.decode("utf-8", errors="replace").rstrip())

    def _write(self, message: dict[str, Any]) -> None:
        if not self._alive() or self._proc is None or self._proc.stdin is None:
            raise DesktopCommanderProviderError("PROVIDER_OFFLINE", "desktop commander local MCP is not running")
        data = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        self._proc.stdin.write(data)
        self._proc.stdin.flush()

    def _request_started(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._request_id += 1
        request_id = self._request_id
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            remaining = max(0.05, deadline - time.monotonic())
            try:
                message = self._messages.get(timeout=min(0.5, remaining))
            except queue.Empty:
                if not self._alive():
                    break
                continue
            if message.get("id") != request_id:
                continue
            if message.get("error"):
                err = message["error"]
                raise DesktopCommanderProviderError(
                    "MCP_PROVIDER_ERROR",
                    str(err.get("message") if isinstance(err, dict) else err),
                )
            return message.get("result")
        detail = "; ".join(list(self._stderr)[-6:])
        raise DesktopCommanderProviderError(
            "MCP_PROVIDER_TIMEOUT",
            f"{method} timed out" + (f": {detail}" if detail else ""),
        )

    def _start(self) -> None:
        node = Path(self.node)
        entry = Path(self.entry)
        if not node.is_file():
            raise DesktopCommanderProviderError("NODE_MISSING", str(node))
        if not entry.is_file():
            raise DesktopCommanderProviderError("DCR_ENTRY_MISSING", str(entry))

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self._messages = queue.Queue()
        self._stderr.clear()
        self._proc = subprocess.Popen(
            [str(node), str(entry)],
            cwd=str(entry.parent),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
        )
        threading.Thread(target=self._reader_loop, args=(self._proc,), daemon=True, name="raios-dcr-stdout").start()
        threading.Thread(target=self._stderr_loop, args=(self._proc,), daemon=True, name="raios-dcr-stderr").start()

        init = self._request_started(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "raios-universal-mcp", "version": "1.1.0"},
            },
        )
        if not isinstance(init, dict):
            raise DesktopCommanderProviderError("MCP_INITIALIZE_INVALID", "initialize returned no object")
        self._write({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        listed = self._request_started("tools/list", {})
        tools = listed.get("tools") if isinstance(listed, dict) else None
        if not isinstance(tools, list):
            raise DesktopCommanderProviderError("MCP_TOOLS_INVALID", "tools/list returned no tools")
        self._tool_names = {
            str(tool.get("name"))
            for tool in tools
            if isinstance(tool, dict) and tool.get("name")
        }

    def _ensure_started(self) -> None:
        if self._alive():
            return
        self.close()
        self._start()

    def status(self, *, start: bool = False) -> dict[str, Any]:
        with self._lock:
            if start:
                self._ensure_started()
            return {
                "provider": "desktop_commander",
                "capability": "remote",
                "transport": "local_stdio",
                "hosted_remote_required": False,
                "running": self._alive(),
                "pid": self._proc.pid if self._alive() and self._proc else None,
                "entry": self.entry,
                "read_tools": sorted(self.read_tools),
                "write_tools": sorted(self.write_tools),
                "discovered_tools": sorted(self._tool_names),
                "stderr_tail": list(self._stderr)[-6:],
            }

    def call(self, operation: str, arguments: dict[str, Any] | None = None, *, read_only: bool = True) -> dict[str, Any]:
        with self._lock:
            self._ensure_started()
            if operation == "__list_tools__":
                return self.status(start=False)
            if operation not in self._tool_names:
                raise DesktopCommanderProviderError("PROVIDER_TOOL_NOT_FOUND", operation)
            allowed = self.read_tools if read_only else self.write_tools
            if operation not in allowed:
                raise DesktopCommanderProviderError("PROVIDER_TOOL_DENIED", operation)
            result = self._request_started(
                "tools/call",
                {"name": operation, "arguments": dict(arguments or {})},
            )
            if not isinstance(result, dict):
                raise DesktopCommanderProviderError("PROVIDER_RESULT_INVALID", operation)
            if result.get("isError"):
                text = json.dumps(result.get("content") or [], ensure_ascii=False)
                raise DesktopCommanderProviderError("PROVIDER_TOOL_ERROR", text[:2000])
            raw = json.dumps(result, ensure_ascii=False, default=str)
            if len(raw) > self.max_result_chars:
                result = {
                    "content": [{"type": "text", "text": raw[: self.max_result_chars]}],
                    "truncated": True,
                }
            return {
                "provider": "desktop_commander",
                "capability": "remote",
                "transport": "local_stdio",
                "hosted_remote_required": False,
                "operation": operation,
                "result": result,
            }

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        self._tool_names.clear()
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
