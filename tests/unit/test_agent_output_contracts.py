from __future__ import annotations

import importlib

import pytest

import agentic_systems.agents as agents_mod
from agentic_systems.final_answer import output_schema
from agentic_systems.results import RunResult

system_mod = importlib.import_module("agentic_systems.system")


def test_agents_output_contract_and_eval_edges():
    result = RunResult(
        text="fallback", data={"answer": 42}, ok=True, engine="python-runtime"
    )
    agents_mod._coerce_output_data(result, None)
    assert result.final == {"answer": 42}

    projected = RunResult(
        text="fallback", data={"answer": 42}, ok=True, engine="python-runtime"
    )
    agents_mod._coerce_output_data(projected, output_schema(["answer"]))
    assert projected.final == {"answer": 42}

    agent = agents_mod.Agent(name="direct", instructions="x", engine="python-runtime")
    with pytest.raises(RuntimeError, match="needs an attached AgenticSystem"):
        agent.eval([])

    with pytest.raises(ValueError, match="policy_tool_budget_too_small"):
        agents_mod.Agent(
            name="budget",
            instructions="x",
            tools=["a", "b"],
            contract={"must_call": ["a", "b"]},
            policy={"max_tool_calls": 1},
        )
