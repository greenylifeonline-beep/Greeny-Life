"""Owned local Desktop Commander adapter using the official MCP SDK.

One admitted call owns one subprocess/session. A timed-out child cannot poison
later calls. No hosted service, shared response queue or second gateway.
"""
from __future__ import annotations

import math
import json
import os
import shutil
import threading
import sys
from pathlib import Path
from typing import Any


class DesktopCommanderProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _positive(config: dict, name: str, default: float) -> float:
    try:
        value = float(config.get(name, default))
        if not math.isfinite(value) or value <= 0:
            raise ValueError(name)
        return value
    except (ValueError, TypeError):
        raise DesktopCommanderProviderError('INVALID_PROVIDER_CONFIG', f'{name} must be finite and positive') from None


def _leaves(error: BaseException):
    nested = getattr(error, 'exceptions', None)
    if nested:
        for child in nested:
            yield from _leaves(child)
    else:
        yield error


class DesktopCommanderProvider:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = dict(config or {})
        self.node = os.getenv('RAIOS_DCR_NODE') or str(self.config.get('node') or shutil.which('node') or 'node')
        default_entry = Path.home() / '.raios/runtime/providers/desktop-commander/current/dist/index.js'
        self.entry = os.getenv('RAIOS_DCR_ENTRY') or str(self.config.get('entry') or default_entry)
        self.timeout_seconds = _positive(self.config, 'timeout_seconds', 30)
        self.admission_timeout_seconds = _positive(self.config, 'admission_timeout_seconds', .1)
        self.max_result_chars = int(_positive(self.config, 'max_result_chars', 20000))
        self.max_tools = int(_positive(self.config, 'max_tools', 1024))
        self.max_frame_bytes = int(_positive(self.config, 'max_frame_bytes', 1024 * 1024))
        self.max_discovery_bytes = int(_positive(self.config, 'max_discovery_bytes', 8 * 1024 * 1024))
        if self.max_tools < 1 or self.max_result_chars < 1:
            raise DesktopCommanderProviderError('INVALID_PROVIDER_CONFIG', 'integer limits must be at least one')
        self.read_tools = set(self.config.get('read_tools') or ())
        self.write_tools = set(self.config.get('write_tools') or ())
        self._slot = threading.BoundedSemaphore(1)
        self._busy = False
        self._closed = False
        self._tools: list[dict] = []

    def status(self, *, start: bool = False) -> dict[str, Any]:
        if start:
            return self.call('__list_tools__')
        tools = list(self._tools)
        return {
            'provider': 'desktop_commander', 'capability': 'remote',
            'transport': 'local_stdio', 'hosted_remote_required': False,
            'sdk': 'mcp', 'session_strategy': 'isolated_per_call',
            'running': self._busy, 'busy': self._busy, 'pid': None,
            'entry': self.entry, 'read_tools': sorted(self.read_tools),
            'write_tools': sorted(self.write_tools),
            'discovered_tools': [t['name'] for t in tools], 'tools': tools,
            'functions': [{'type': 'function', 'function': {
                'name': t['name'], 'description': t.get('description') or '',
                'parameters': t['inputSchema']}} for t in tools],
            'timeout_seconds': self.timeout_seconds,
        }

    async def _execute(self, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        import anyio
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters
        from .bounded_stdio import bounded_stdio_client

        command = shutil.which(self.node) or self.node
        if not Path(command).is_file():
            raise DesktopCommanderProviderError('NODE_MISSING', 'configured provider executable is missing')
        entry = Path(self.entry).expanduser().resolve()
        if not entry.is_file():
            raise DesktopCommanderProviderError('DCR_ENTRY_MISSING', 'configured provider entrypoint is missing')
        parameters = StdioServerParameters(command=command, args=[str(entry)], cwd=str(entry.parent))
        # No provider stderr text is returned to clients or copied into audit.
        with open(os.devnull, 'w') as errlog, anyio.fail_after(self.timeout_seconds):
            async with bounded_stdio_client(parameters, max_frame_bytes=self.max_frame_bytes, errlog=errlog) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    discovered: list[dict] = []
                    cursor = None
                    seen_cursors = set()
                    names = set()
                    discovery_bytes = 0
                    while True:
                        listed = await session.list_tools(cursor=cursor)
                        for tool in listed.tools:
                            discovery_bytes += len(tool.model_dump_json().encode('utf-8'))
                            if discovery_bytes > self.max_discovery_bytes:
                                raise DesktopCommanderProviderError('MCP_TOOLS_INVALID', 'provider discovery exceeds configured byte limit')
                            if tool.name in names or len(names) >= self.max_tools:
                                raise DesktopCommanderProviderError('MCP_TOOLS_INVALID', 'duplicate or excessive provider tools')
                            names.add(tool.name)
                            if tool.name in self.read_tools | self.write_tools:
                                discovered.append(tool.model_dump(by_alias=True, exclude_none=True))
                        cursor = listed.nextCursor
                        if not cursor:
                            break
                        if cursor in seen_cursors:
                            raise DesktopCommanderProviderError('MCP_TOOLS_INVALID', 'provider pagination repeats')
                        discovery_bytes += len(cursor.encode('utf-8'))
                        if len(seen_cursors) >= self.max_tools or discovery_bytes > self.max_discovery_bytes:
                            raise DesktopCommanderProviderError('MCP_TOOLS_INVALID', 'provider pagination exceeds configured limit')
                        seen_cursors.add(cursor)
                    self._tools = discovered
                    if operation == '__list_tools__':
                        return self.status()
                    tool = next((t for t in discovered if t['name'] == operation), None)
                    if tool is None:
                        raise DesktopCommanderProviderError('PROVIDER_TOOL_NOT_FOUND', 'operation unavailable at provider')
                    validation_input = json.dumps({'schema': tool['inputSchema'], 'arguments': arguments}).encode('utf-8')
                    if len(validation_input) > self.max_frame_bytes:
                        raise DesktopCommanderProviderError('INVALID_ARGUMENTS', 'schema and arguments exceed configured frame limit')
                    validation = await anyio.run_process(
                        [sys.executable, str(Path(__file__).with_name('schema_validator.py'))],
                        input=validation_input, stdout=-3, stderr=-3, check=False)
                    if validation.returncode != 0:
                        raise DesktopCommanderProviderError('INVALID_ARGUMENTS', 'arguments do not match provider tool schema')
                    result = await session.call_tool(operation, arguments)
                    if result.isError:
                        raise DesktopCommanderProviderError('PROVIDER_TOOL_ERROR', 'provider reported an execution error')
                    raw = result.model_dump_json(by_alias=True, exclude_none=True)
                    if len(raw) > self.max_result_chars:
                        raise DesktopCommanderProviderError('PROVIDER_RESULT_TOO_LARGE', 'provider result exceeds configured limit')
                    return {'provider': 'desktop_commander', 'capability': 'remote',
                        'transport': 'local_stdio', 'hosted_remote_required': False,
                        'operation': operation, 'result': result.model_dump(by_alias=True, exclude_none=True)}

    def call(self, operation: str, arguments: dict[str, Any] | None = None, *, read_only: bool = True) -> dict[str, Any]:
        allowed = self.read_tools if read_only else self.write_tools
        if operation != '__list_tools__' and operation not in allowed:
            raise DesktopCommanderProviderError('PROVIDER_TOOL_DENIED', 'operation is not permitted by provider policy')
        if arguments is not None and not isinstance(arguments, dict):
            raise DesktopCommanderProviderError('INVALID_ARGUMENTS', 'arguments must be an object')
        if self._closed:
            raise DesktopCommanderProviderError('PROVIDER_CLOSED', 'provider adapter has been closed')
        if not self._slot.acquire(timeout=self.admission_timeout_seconds):
            raise DesktopCommanderProviderError('PROVIDER_BUSY', 'provider capacity is occupied; retry later')
        try:
            if self._closed:
                raise DesktopCommanderProviderError('PROVIDER_CLOSED', 'provider adapter has been closed')
            self._busy = True
            try:
                import anyio
                return anyio.run(self._execute, operation, dict(arguments or {}))
            except ImportError:
                raise DesktopCommanderProviderError('PROVIDER_DEPENDENCY_MISSING', 'install the pinned RAIOS MCP requirements') from None
            except Exception as error:
                from .bounded_stdio import ProviderTransportError
                leaves = list(_leaves(error))
                for leaf in leaves:
                    if isinstance(leaf, DesktopCommanderProviderError):
                        raise leaf from None
                    if isinstance(leaf, ProviderTransportError):
                        raise DesktopCommanderProviderError(leaf.code, 'provider framing failed; session discarded') from None
                if any(isinstance(leaf, TimeoutError) for leaf in leaves):
                    raise DesktopCommanderProviderError('MCP_PROVIDER_TIMEOUT', 'provider deadline exceeded; session discarded') from None
                raise DesktopCommanderProviderError('MCP_PROVIDER_ERROR', 'local provider session failed; session discarded') from None
        finally:
            self._busy = False
            self._slot.release()

    def close(self) -> None:
        # Each admitted call owns its child and performs SDK cleanup within its
        # deadline. Closing prevents further admission without blocking health.
        self._closed = True
