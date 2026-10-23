import asyncio
from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
import sys
import time


@contextmanager
def local_service(kind, budget=None):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    logs = (budget.path.parent if budget else Path.cwd() / ".tmp/studio-protocols") / "protocol-logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / (kind + "-" + str(port) + ".log")
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, str(Path(__file__).with_name("protocol_server.py")), kind, "--port", str(port)],
        stdout=log, stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if budget:
        budget.local_protocol_ports.add(port)
    try:
        deadline = time.monotonic() + 45
        while True:
            if process.poll() is not None:
                raise RuntimeError(kind + " service exited before startup: " + log_path.read_text(encoding="utf-8", errors="replace")[-3000:])
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError(kind + " service startup")
                time.sleep(0.05)
        yield "http://127.0.0.1:" + str(port)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        if budget:
            budget.local_protocol_ports.discard(port)
        log.close()


@contextmanager
def strands_tools(kind, budget=None):
    with local_service(kind, budget) as endpoint:
        if kind == "mcp":
            from mcp.client.streamable_http import streamable_http_client
            from strands.tools.mcp import MCPClient
            client = MCPClient(lambda: streamable_http_client(endpoint + "/mcp"))
            try:
                yield [client], {"transport": "mcp-streamable-http"}
            finally:
                client.stop(None, None, None)
        else:
            from strands.agent.a2a_agent import A2AAgent
            from strands import tool
            remote = A2AAgent(endpoint=endpoint, name="remote_evidence", timeout=30)
            card = asyncio.run(remote.get_agent_card())
            assert card.name == "agentic_systems_a2a_echo"

            @tool
            def call_remote_echo(value: str) -> dict:
                """Call the remote A2A agent over its actual local HTTP endpoint."""
                import json
                reply = remote(json.dumps({"tool": "echo", "input": {"value": value}}))
                text = "".join(block.get("text", "") for block in reply.message.get("content", []))
                if value not in text or "a2a" not in text:
                    raise ValueError("Remote agent did not preserve the requested evidence: " + text[:1000])
                return {"value": value, "transport": "a2a", "remote_text": text}
            yield [call_remote_echo], {"transport": "a2a", "agent_card": card.name}
