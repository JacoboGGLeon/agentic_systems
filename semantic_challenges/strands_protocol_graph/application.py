"""Executable semantic challenge: Strands MCP + A2A under LangGraph."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4

from mcp.client.stdio import StdioServerParameters, stdio_client
from strands import tool as strands_tool
from strands.agent.a2a_agent import A2AAgent
from strands.tools.mcp import MCPClient

import agentic_systems as toolkit
from agentic_systems.core.runtime import _load_dotenv
from agentic_systems.registry import PROVIDERS as CANONICAL_PROVIDERS
from agentic_systems.registry import provider_capability, provider_definition


ROOT = Path(__file__).resolve().parent
PROVIDERS = tuple(item.name for item in CANONICAL_PROVIDERS)
CRITERIA = (
    "request_fulfillment",
    "evidence_correctness",
    "clarity",
    "no_technical_noise",
    "identity_integrity",
    "lineage_integrity",
)


def load_canonical_dotenv(path: Path) -> bool:
    """Load `.env` with explicit precedence; process env is fallback only."""

    return _load_dotenv(path=path, override=True)


def live_enabled(provider: str) -> bool:
    definition = provider_definition(provider)
    if definition.live_flag is None:
        return provider == "python-runtime"
    value = os.getenv(definition.live_flag, "0").strip().lower()
    return value in {"1", "true", "yes"}


def new_evidence_tokens() -> tuple[str, str]:
    """Create opaque per-episode evidence that cannot be memorized by a model."""

    return (
        f"MCP-{secrets.token_hex(8).upper()}",
        f"A2A-{secrets.token_hex(8).upper()}",
    )


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
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("The local A2A server did not become ready within 60 seconds.")


@asynccontextmanager
async def _mcp_transport() -> AsyncIterator[Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_server.py")],
    )
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        async with stdio_client(parameters, errlog=errlog) as transport:
            yield transport


def _a2a_text(result: Any) -> str:
    message = getattr(result, "message", {})
    if not isinstance(message, Mapping):
        return str(message)
    content = message.get("content", ())
    if not isinstance(content, list):
        return str(content)
    return "".join(
        str(block.get("text", "")) for block in content if isinstance(block, Mapping)
    )


def _contains_subset(value: Any, expected: Any) -> bool:
    if isinstance(expected, Mapping):
        return isinstance(value, Mapping) and all(
            key in value and _contains_subset(value[key], item)
            for key, item in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(value, list)
            and len(value) == len(expected)
            and all(
                _contains_subset(actual, declared)
                for actual, declared in zip(value, expected, strict=True)
            )
        )
    return value == expected


@toolkit.tool
def certify_protocol_episode(request: dict[str, Any]) -> dict[str, Any]:
    """Deterministically certify public answer, identity, tools, and lineage."""

    case = request.get("case") if isinstance(request.get("case"), dict) else {}
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    candidate = (
        request.get("candidate") if isinstance(request.get("candidate"), dict) else {}
    )
    executions = candidate.get("executions") or []
    root = executions[0] if executions and isinstance(executions[0], dict) else {}
    child = (
        executions[1] if len(executions) > 1 and isinstance(executions[1], dict) else {}
    )
    answer = str((root.get("answer") or {}).get("text") or "").strip()
    child_tools = child.get("tools") if isinstance(child.get("tools"), list) else []
    names = [str(item.get("name")) for item in child_tools if isinstance(item, dict)]
    outputs = {
        str(item.get("name")): item.get("output")
        for item in child_tools
        if isinstance(item, dict)
    }
    root_runtime = root.get("runtime") if isinstance(root.get("runtime"), dict) else {}
    child_runtime = (
        child.get("runtime") if isinstance(child.get("runtime"), dict) else {}
    )
    expected_tools = [str(item) for item in expected.get("tool_path") or []]
    expected_outputs = expected.get("tool_output_contains") or {}
    expected_route = expected.get("execution_path") or []
    fragments = expected.get("text_contains") or []
    if isinstance(fragments, str):
        fragments = [fragments]
    exact_tools = names == expected_tools
    evidence_ok = bool(expected_outputs) and all(
        _contains_subset(outputs.get(str(tool_name)), subset)
        for tool_name, subset in expected_outputs.items()
    )
    actual_route = [
        {
            "provider": root_runtime.get("provider"),
            "framework": root_runtime.get("framework"),
        },
        {
            "provider": child_runtime.get("provider"),
            "framework": child_runtime.get("framework"),
        },
    ]
    identity_ok = _contains_subset(actual_route, expected_route)
    clear = bool(fragments) and all(
        str(fragment).lower() in answer.lower() for fragment in fragments
    )
    no_noise = not answer.lstrip().startswith(("{", "[")) and not any(
        marker in answer.lower()
        for marker in ("toolenvelope", "<thinking>", "<reasoning>", "traceback")
    )
    lineage_ok = len(executions) == len(expected_route) and exact_tools
    criteria = {
        "request_fulfillment": float(clear and evidence_ok),
        "evidence_correctness": float(evidence_ok and exact_tools),
        "clarity": float(clear),
        "no_technical_noise": float(no_noise),
        "identity_integrity": float(identity_ok),
        "lineage_integrity": float(lineage_ok),
    }
    failed = [name for name, score in criteria.items() if score < 1.0]
    return {
        "score": sum(criteria.values()) / len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "rationale": "All declared evidence and routes agree."
        if not failed
        else ", ".join(failed),
        "provider": "python-runtime",
        "framework": "native",
        "model": "python-runtime",
    }


class NativeProtocolJudge:
    """Adapter that forces every judge verdict through a deterministic Tool."""

    def __init__(self) -> None:
        runtime = toolkit.runtime(provider="python-runtime", model="python-runtime")
        self.agent = toolkit.agent(
            name="native_protocol_judge",
            instructions="Execute certify_protocol_episode exactly once.",
            runtime=runtime,
            framework="native",
            tools=[certify_protocol_episode],
            contract=toolkit.AgentContract(must_call=["certify_protocol_episode"]),
            policy=toolkit.RunPolicy(
                max_turns=2,
                max_tool_calls=1,
                tool_choice="certify_protocol_episode",
                temperature=0.0,
            ),
        )

    def run(self, request: dict[str, Any], mode: str = "eval") -> toolkit.RunResult:
        return self.agent.run(
            {"tool": "certify_protocol_episode", "input": {"request": request}},
            mode=mode,
        )


class ProtocolChallenge:
    """Own protocol resources and expose one LangGraph-backed Executable."""

    def __init__(self, provider: str, *, model: str | None = None) -> None:
        if provider not in PROVIDERS:
            raise ValueError(f"Unsupported challenge provider {provider!r}.")
        self.provider = provider
        self.model_generation = (
            provider_capability(provider, "model_generation").status != "unsupported"
        )
        runtime_probe = toolkit.runtime(provider=provider, model=model)
        self.model = str(runtime_probe.model_id or "").strip()
        if not self.model:
            raise ValueError(f"No model resolved from .env for {provider!r}.")
        self.a2a_process: subprocess.Popen[Any] | None = None
        self.mcp_client: MCPClient | None = None
        self.remote: A2AAgent | None = None
        self.last_result: toolkit.RunResult | None = None
        self._compiled: Any = None
        self._graph_type = ""
        self.system: Any = None
        self.candidate: Any = None
        self.judge = NativeProtocolJudge()

    def __enter__(self) -> "ProtocolChallenge":
        port = _free_port()
        self.a2a_process = subprocess.Popen(
            [sys.executable, str(ROOT / "a2a_server.py"), "--port", str(port)],
            cwd=ROOT.parents[1],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_for_port(self.a2a_process, port)
        self.remote = A2AAgent(
            endpoint=f"http://127.0.0.1:{port}",
            name="protocol_evidence_agent",
            description="Remote deterministic Agent returning A2A evidence.",
            timeout=30,
        )
        card = asyncio.run(self.remote.get_agent_card())
        if card.name != "protocol_evidence_agent":
            raise RuntimeError(f"Unexpected A2A Agent Card {card.name!r}.")

        remote = self.remote

        @strands_tool
        def fetch_a2a_evidence(token: str) -> dict[str, str]:
            """Retrieve verified evidence from the remote A2A Agent."""

            response = remote(
                json.dumps({"tool": "fetch_remote_evidence", "input": {"token": token}})
            )
            return {
                "protocol": "a2a",
                "token": token,
                "status": "verified",
                "remote_evidence": _a2a_text(response),
            }

        self.mcp_client = MCPClient(_mcp_transport)
        runtime = toolkit.runtime(
            provider=self.provider,
            model=self.model,
            scheduler=toolkit.scheduler(
                max_turns=4,
                max_tool_calls=2,
                timeout_s=120,
                max_retries=0,
                max_concurrency=1,
            ),
        )
        self.system = toolkit.system(runtime=runtime, model=self.model)
        self.candidate = self.system.agent(
            name="strands_protocol_agent",
            instructions=(
                "For every request, call fetch_mcp_evidence exactly once with the MCP "
                "token and fetch_a2a_evidence exactly once with the A2A token. Use no "
                "other tools. Then write two concise natural sentences confirming both "
                "protocols and both exact tokens. Never expose JSON, ToolEnvelope, code, "
                "or private reasoning."
            ),
            framework=toolkit.framework(
                "strands",
                agent_kwargs={"tools": [self.mcp_client, fetch_a2a_evidence]},
            ),
            policy=toolkit.RunPolicy(
                max_turns=4,
                max_tool_calls=2,
                max_tokens=500,
                temperature=0.0,
                tool_choice="auto",
            ),
        )
        graph = self.system.graph(name="strands_protocol_graph", state=dict)

        def candidate_node(state: dict[str, Any]) -> dict[str, Any]:
            return {
                **state,
                "candidate_result": self.candidate.run(state["prompt"], mode="eval"),
            }

        def finalize_node(state: dict[str, Any]) -> dict[str, Any]:
            child: toolkit.RunResult = state["candidate_result"]
            public_text = child.text
            if not self.model_generation and child.ok:
                outputs = {event.name: event.output for event in child.tool_events}
                mcp_evidence = outputs.get("fetch_mcp_evidence") or {}
                a2a_evidence = outputs.get("fetch_a2a_evidence") or {}
                public_text = (
                    f"MCP verified {mcp_evidence.get('token')}. "
                    f"A2A verified {a2a_evidence.get('token')}."
                )
            root = toolkit.RunResult(
                text=public_text,
                final={"text": public_text},
                data={
                    "graph": {"engine": "langgraph", "native_type": self._graph_type},
                    "protocols": ["mcp", "a2a"],
                },
                ok=child.ok,
                usage=dict(child.usage),
                engine=self.provider,
                model=self.model,
                mode="eval",
                errors=list(child.errors),
                meta={
                    "input": state["prompt"],
                    "system_name": "strands_protocol_system",
                    "runtime_engine": self.provider,
                    "framework_adapter": "langgraph",
                    "graph_native_type": self._graph_type,
                    "fallback_provider": None,
                },
                execution_id=f"protocol_graph_{uuid4().hex}",
            )
            root.add_child(child)
            root.raise_if_inconsistent()
            return {**state, "result": root}

        graph.add_node("strands_candidate", candidate_node)
        graph.add_node("finalize_public_result", finalize_node)
        graph.edge("START", "strands_candidate")
        graph.edge("strands_candidate", "finalize_public_result")
        graph.edge("finalize_public_result", "END")
        self._compiled = graph.compile()
        self._graph_type = type(self._compiled).__name__
        return self

    def run(
        self,
        prompt: Any,
        *,
        mode: str = "eval",
        config: Any = None,
    ) -> toolkit.RunResult:
        del mode, config
        if self._compiled is None:
            raise RuntimeError("ProtocolChallenge must be used as a context manager.")
        state = self._compiled.invoke({"prompt": prompt})
        result: toolkit.RunResult = state["result"]
        self.last_result = result
        return result

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.mcp_client is not None:
            self.mcp_client.stop(None, None, None)
        if self.a2a_process is not None:
            self.a2a_process.terminate()
            try:
                self.a2a_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.a2a_process.kill()
                self.a2a_process.wait(timeout=10)


def challenge_case(
    provider: str,
    model: str,
    *,
    mcp_token: str,
    a2a_token: str,
) -> dict[str, Any]:
    natural_prompt = (
        f"Obtain {mcp_token} through MCP and {a2a_token} through A2A. "
        "Use each protocol exactly once, then explain the verified evidence naturally."
    )
    input_value: Any = natural_prompt
    if provider_capability(provider, "model_generation").status == "unsupported":
        input_value = {
            "steps": [
                {
                    "tool": "fetch_mcp_evidence",
                    "input": {"token": mcp_token},
                },
                {
                    "tool": "fetch_a2a_evidence",
                    "input": {"token": a2a_token},
                },
            ]
        }
    return {
        "name": "mcp_a2a_protocol_synthesis",
        "input": input_value,
        "expected": {
            "ok": True,
            "text_contains": [mcp_token, a2a_token],
            "human_answer": True,
            "provider": provider,
            "model": model,
            "framework": "strands",
            "no_fallback": True,
            "tool_path": ["fetch_mcp_evidence", "fetch_a2a_evidence"],
            "tool_output_contains": {
                "fetch_mcp_evidence": {
                    "protocol": "mcp",
                    "token": mcp_token,
                    "status": "verified",
                },
                "fetch_a2a_evidence": {
                    "protocol": "a2a",
                    "token": a2a_token,
                    "status": "verified",
                },
            },
            "execution_path": [
                {"provider": provider, "framework": "langgraph"},
                {"provider": provider, "framework": "strands"},
            ],
        },
    }


def judge_rubric() -> toolkit.JudgeRubric:
    return toolkit.JudgeRubric(
        criteria=list(CRITERIA),
        threshold=1.0,
        certification_tool="certify_protocol_episode",
    )
