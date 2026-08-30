FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONUNBUFFERED=1
# Mount the repository at /workspace.
# Streamable HTTP MCP: POST /mcp  Health: GET /health
# TLS belongs on the reverse proxy / Secure MCP Tunnel. No WebSocket. No SQLite.
EXPOSE 8787
CMD ["python3", "scripts/ai-os/raios_mcp/server.py", "--http", "--host", "0.0.0.0", "--port", "8787"]
