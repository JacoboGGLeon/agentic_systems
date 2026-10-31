"""Actual local MCP/A2A with an SDK fixture; no model inference."""

import pydantic
import json
from pathlib import Path
import tempfile
import agentic_systems as toolkit
from agentic_systems_studio.budget import CampaignBudget
from agentic_systems_studio.lab.protocols import strands_tools
from agentic_systems_studio.lab.native_profiles import strands_fixture_model


class State(pydantic.BaseModel):
    value: str
    response: str | None = None
    protocol: str | None = None


def run():
    from strands import Agent as StrandsAgent

    budget = CampaignBudget(
        Path(tempfile.mkdtemp()) / "protocol-budget.json",
        {},
        "local-protocols",
        usd=0,
        requests=0,
    )
    budget.install()
    rows = []
    for kind in ("mcp", "a2a"):
        with strands_tools(kind, budget) as (tools, witness):
            native = StrandsAgent(
                model=strands_fixture_model(), tools=tools, callback_handler=None
            )
            name = "echo" if kind == "mcp" else "call_remote_echo"

            @toolkit.tool
            def roundtrip(value: str) -> dict:
                raw = native(json.dumps({"tool": name, "input": {"value": value}}))
                response = str(raw)
                assert value in response and kind in response, response
                return {"response": response, "protocol": kind}

            graph = toolkit.Graph(State)
            graph.add_node("roundtrip", roundtrip)
            graph.add_edge(toolkit.START, "roundtrip")
            graph.add_edge("roundtrip", toolkit.END)
            result = toolkit.Agent("local_" + kind, graph=graph).run(
                {"value": "FRAMEWORKS_TOGETHER"}, timeout_s=90
            )
            assert result.ok, result.to_dict()
            rows.append(
                {"protocol": kind, "witness": witness, "result": result.to_dict()}
            )
    assert budget.summary()["attempts"] == 0
    return {
        "rows": rows,
        "inference_requests": 0,
        "scope": "native Strands SDK fixture over real loopback transports, wrapped as deterministic Tool; public LM adapter tested separately online",
    }
