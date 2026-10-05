"""Bounded framing around the pinned official SDK session and process lifecycle.

SDK 1.30's default stdio reader buffers an unlimited line and logs bad payloads.
Keep its protocol models/session and Windows Job Object/POSIX process-group
cleanup, but impose a byte limit before parsing and sanitize framing failures.
"""
from contextlib import asynccontextmanager


class ProviderTransportError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@asynccontextmanager
async def bounded_stdio_client(parameters, *, max_frame_bytes: int, errlog):
    import anyio
    from mcp import types
    from mcp.client.stdio import _create_platform_compatible_process, _terminate_process_tree
    from mcp.shared.message import SessionMessage

    read_send, read_receive = anyio.create_memory_object_stream(0)
    write_send, write_receive = anyio.create_memory_object_stream(0)
    process = await _create_platform_compatible_process(
        parameters.command, parameters.args, None, errlog, parameters.cwd)

    async def read_frames():
        buffer = bytearray()
        while True:
            try:
                chunk = await process.stdout.receive(65536)
            except anyio.EndOfStream:
                if buffer:
                    raise ProviderTransportError('MCP_PROVIDER_PROTOCOL_ERROR')
                return
            # Limit every partial line before copying/decoding/JSON parsing.
            for part in chunk.splitlines(keepends=True):
                if len(buffer) + len(part) > max_frame_bytes:
                    raise ProviderTransportError('PROVIDER_FRAME_TOO_LARGE')
                buffer.extend(part)
                if not buffer.endswith(b'\n'):
                    continue
                raw = bytes(buffer).strip()
                buffer.clear()
                if not raw:
                    continue
                try:
                    message = types.JSONRPCMessage.model_validate_json(raw)
                except Exception:
                    raise ProviderTransportError('MCP_PROVIDER_PROTOCOL_ERROR') from None
                await read_send.send(SessionMessage(message))

    async def write_frames():
        async with write_receive:
            async for item in write_receive:
                raw = item.message.model_dump_json(by_alias=True, exclude_none=True).encode('utf-8') + b'\n'
                if len(raw) > max_frame_bytes:
                    raise ProviderTransportError('PROVIDER_FRAME_TOO_LARGE')
                await process.stdin.send(raw)

    async with process, anyio.create_task_group() as group:
        group.start_soon(read_frames)
        group.start_soon(write_frames)
        try:
            yield read_receive, write_send
        finally:
            group.cancel_scope.cancel()
            with anyio.CancelScope(shield=True):
                # Each call owns this process tree. End it even on success, EOF,
                # cancellation or invalid framing; no shared session survives.
                try:
                    await _terminate_process_tree(process)
                finally:
                    await read_send.aclose()
                    await read_receive.aclose()
                    await write_send.aclose()
                    await write_receive.aclose()
