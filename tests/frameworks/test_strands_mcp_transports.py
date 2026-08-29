from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial
from pathlib import Path
import socket
import os
import subprocess
import sys
import time
from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
import pytest
from strands.tools.mcp import MCPClient

import agentic_systems as toolkit


SERVER = (
    Path(__file__).resolve().parents[2] / "tutorials" / "frameworks" / "mcp_echo_server.py"
)


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_port(process: subprocess.Popen[bytes], port: int) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The local Streamable HTTP MCP server exited early.")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(
        "The local Streamable HTTP MCP server did not start within 60 seconds."
    )


@asynccontextmanager
async def _stdio_transport() -> AsyncIterator[Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER), "--transport", "stdio"],
    )
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        async with stdio_client(parameters, errlog=errlog) as transport:
            yield transport


@pytest.mark.parametrize("transport", ["stdio", "streamable-http"])
def test_strands_executes_native_mcp_tool_over_local_transport(transport: str):
    process: subprocess.Popen[bytes] | None = None
    client: MCPClient | None = None
    try:
        transport_factory: Callable[[], AbstractAsyncContextManager[Any]]
        if transport == "stdio":
            transport_factory = _stdio_transport
        else:
            port = _free_port()
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(SERVER),
                    "--transport",
                    "streamable-http",
                    "--port",
                    str(port),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _wait_for_port(process, port)
            transport_factory = partial(
                streamable_http_client,
                f"http://127.0.0.1:{port}/mcp",
            )

        client = MCPClient(transport_factory)
        agent = toolkit.agent(
            name=f"strands_mcp_{transport}",
            instructions="Execute the requested MCP tool.",
            runtime=toolkit.runtime(provider="python-runtime"),
            framework=toolkit.framework(
                "strands",
                agent_kwargs={"tools": [client]},
            ),
        )
        result = agent.run(
            {"tool": "echo", "input": {"value": "verified"}},
            mode="eval",
        )
    finally:
        if client is not None:
            client.stop(None, None, None)
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    assert result.ok is True
    assert result.meta["framework_adapter"] == "strands"
    assert result.engine == "python-runtime"
    assert [event.name for event in result.tool_events] == ["echo"]
    assert result.data == {
        "value": "verified",
        "transport": transport,
    }
    assert result.tool_events[0].output == {
        "value": "verified",
        "transport": transport,
    }
