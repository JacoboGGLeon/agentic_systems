from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any

import pytest

pytest.importorskip("a2a")

from strands import tool as strands_tool
from strands.agent.a2a_agent import A2AAgent

import agentic_systems as toolkit


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "tutorials" / "frameworks" / "a2a_echo_server.py"


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_port(process: subprocess.Popen[Any], port: int) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The local A2A server exited before becoming ready.")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("The local A2A server did not become ready within 60 seconds.")


def _message_text(result: Any) -> str:
    message = getattr(result, "message", {})
    if not isinstance(message, Mapping):
        return str(message)
    content = message.get("content", ())
    if not isinstance(content, list):
        return str(content)
    return "".join(
        str(block.get("text", ""))
        for block in content
        if isinstance(block, Mapping)
    )


def test_strands_a2a_agent_executes_remote_agent_as_native_tool(tmp_path: Path) -> None:
    port = _free_port()
    stdout_path = tmp_path / "a2a-server.stdout.log"
    stderr_path = tmp_path / "a2a-server.stderr.log"

    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        process = subprocess.Popen(
            [sys.executable, str(SERVER), "--port", str(port)],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
        )

    try:
        _wait_for_port(process, port)
        remote = A2AAgent(
            endpoint=f"http://127.0.0.1:{port}",
            name="remote_echo",
            description="Remote deterministic echo Agent.",
            timeout=30,
        )
        card = asyncio.run(remote.get_agent_card())
        assert card.name == "agentic_systems_a2a_echo"

        @strands_tool
        def call_remote_echo(value: str) -> dict[str, str]:
            response = remote(
                json.dumps({"tool": "echo", "input": {"value": value}})
            )
            return {"value": value, "remote_text": _message_text(response)}

        agent = toolkit.agent(
            name="strands_a2a_client",
            instructions="Execute the requested remote A2A Tool.",
            runtime=toolkit.runtime(provider="python-runtime"),
            framework=toolkit.framework(
                "strands",
                agent_kwargs={"tools": [call_remote_echo]},
            ),
        )
        result = agent.run(
            {"tool": "call_remote_echo", "input": {"value": "verified"}},
            mode="eval",
        )

        assert result.ok, result.errors
        assert result.engine == "python-runtime"
        assert result.meta["framework_adapter"] == "strands"
        assert [event.name for event in result.tool_events] == ["call_remote_echo"]
        assert "verified" in json.dumps(result.data)
        assert "a2a" in json.dumps(result.data).lower()
        result.raise_if_inconsistent()
    except Exception as exc:
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        raise AssertionError(
            f"A2A integration failed.\nstdout:\n{stdout_text}\nstderr:\n{stderr_text}"
        ) from exc
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
