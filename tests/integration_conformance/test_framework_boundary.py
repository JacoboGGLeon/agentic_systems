"""Checkpoint 1.1.5 Framework and Graph boundary conformance."""

from __future__ import annotations

import asyncio
import json

import pytest

from agentic_systems import Agent, RunResult, tool
from agentic_systems.engines.names import (
    LANGGRAPH_ORCHESTRATOR,
    OPENAI_AGENTS_FRAMEWORK,
    PYTHON_RUNTIME_ENGINE,
    STRANDS_FRAMEWORK,
)
from agentic_systems.environments import AgentStepGraph
from agentic_systems.integrations import (
    PRESERVED_RUN_RESULT_FIELDS,
    FrameworkProjectionReport,
    describe_graph_boundary,
    evaluate_framework_projection,
    framework_profile,
    framework_profiles,
)
from agentic_systems.integrations.langgraph import GraphApp, build_langgraph_agent_node
from agentic_systems.tools.compat import ToolEvent


def _result() -> RunResult:
    result = RunResult(
        text="42",
        data={"result": 42},
        ok=True,
        tool_events=[
            ToolEvent(
                id="call-double",
                name="double",
                input={"value": 21},
                output={"result": 42},
                ok=True,
            )
        ],
        usage={"total_tokens": 5},
        engine=PYTHON_RUNTIME_ENGINE,
        model="conformance-model",
        mode="conformance",
    )
    return result.apply_validation(result.validate())


class ResultAgent:
    name = "result-agent"

    def __init__(self, result: RunResult) -> None:
        self.result = result

    def run(self, input, *, mode="default", config=None):
        return self.result


def test_framework_profiles_distinguish_real_and_declarative_integrations() -> None:
    profiles = framework_profiles()

    assert [profile.framework for profile in profiles] == [
        LANGGRAPH_ORCHESTRATOR,
        OPENAI_AGENTS_FRAMEWORK,
        STRANDS_FRAMEWORK,
    ]
    assert [profile.integration_kind for profile in profiles] == [
        "native-adapter",
        "style-only",
        "declarative-only",
    ]
    assert framework_profile(LANGGRAPH_ORCHESTRATOR).check(require_adapter=True).ok is True

    for name in (OPENAI_AGENTS_FRAMEWORK, STRANDS_FRAMEWORK):
        profile = framework_profile(name)
        validation = profile.check(require_adapter=True)
        assert profile.has_adapter is False
        assert validation.ok is False
        assert validation.issues[0].code == "framework_adapter_unavailable"
        assert json.loads(json.dumps(profile.to_dict()))["framework"] == name

    with pytest.raises(ValueError, match="Unknown framework"):
        framework_profile("unknown-framework")


def test_langgraph_node_preserves_run_result_in_explicit_state_projection() -> None:
    source = _result()
    node = build_langgraph_agent_node(
        ResultAgent(source),
        input="prompt",
        output="answer",
        trace="trace",
        result_key="result",
        mode="conformance",
    )

    state = node({"prompt": "double 21"})
    report = evaluate_framework_projection(
        LANGGRAPH_ORCHESTRATOR,
        source_result=source,
        projected_state=state,
        result_key="result",
        trace_key="trace",
    )

    assert report.raise_if_failed().ok is True
    assert all(report.checks.values())
    assert state["answer"] == "42"
    assert state["result"]["meta"]["framework_adapter"] == LANGGRAPH_ORCHESTRATOR
    assert set(PRESERVED_RUN_RESULT_FIELDS).issubset(state["result"])
    assert json.loads(json.dumps(report.to_dict()))["framework"] == LANGGRAPH_ORCHESTRATOR


def test_framework_projection_failures_are_structured() -> None:
    unavailable = evaluate_framework_projection(
        STRANDS_FRAMEWORK,
        source_result=object(),
        projected_state=object(),
        result_key="result",
    )
    assert unavailable.ok is False
    assert unavailable.checks == {
        "adapter_available": False,
        "source_run_result": False,
        "state_mapping": False,
    }
    assert {issue["code"] for issue in unavailable.issues} == {
        "adapter_available",
        "framework_adapter_unavailable",
        "source_run_result",
        "state_mapping",
    }
    with pytest.raises(ValueError, match="Framework projection failed"):
        unavailable.raise_if_failed()

    missing = evaluate_framework_projection(
        LANGGRAPH_ORCHESTRATOR,
        source_result=_result(),
        projected_state={},
        result_key="result",
        trace_key="trace",
    )
    assert missing.checks["result_projection"] is False
    assert missing.checks["trace_projection"] is False

    source = _result()
    projected = source.to_dict()
    projected["meta"] = {"framework_adapter": LANGGRAPH_ORCHESTRATOR}
    not_serializable = evaluate_framework_projection(
        LANGGRAPH_ORCHESTRATOR,
        source_result=source,
        projected_state={"result": projected, "bad": object()},
        result_key="result",
    )
    assert not_serializable.checks["json_serialization"] is False

    manual = FrameworkProjectionReport(
        framework=LANGGRAPH_ORCHESTRATOR,
        ok=True,
        checks={},
        issues=[],
    )
    assert manual.raise_if_failed() is manual


class NativeApp:
    def invoke(self, state):
        return {**state, "visited": True}

    async def ainvoke(self, state):
        return {**state, "visited": "async"}


def test_native_and_framework_graph_boundaries_are_distinct() -> None:
    portable = AgentStepGraph(ResultAgent(_result()), input="prompt")
    external = GraphApp(native=NativeApp(), engine=LANGGRAPH_ORCHESTRATOR, name="external")

    portable_boundary = describe_graph_boundary(portable)
    external_boundary = describe_graph_boundary(external)

    assert portable_boundary.kind == "agentic-systems-native"
    assert portable_boundary.framework is None
    assert portable_boundary.native_type == "AgentStepGraph"
    assert external_boundary.kind == "framework-native"
    assert external_boundary.framework == LANGGRAPH_ORCHESTRATOR
    assert external_boundary.native_type == "NativeApp"
    assert json.loads(json.dumps(external_boundary.to_dict()))["kind"] == "framework-native"
    assert external.run({"x": 1})["visited"] is True
    assert asyncio.run(external.arun({"x": 1}))["visited"] == "async"

    with pytest.raises(TypeError, match="Graph boundary is not declared"):
        describe_graph_boundary(object())

    class InvalidExternal:
        graph_kind = "framework-native"
        framework = None

    with pytest.raises(ValueError, match="must declare its framework"):
        describe_graph_boundary(InvalidExternal())


@tool
def double(value: int) -> dict:
    return {"result": value * 2}


def test_agent_metadata_separates_requested_framework_from_executed_adapter() -> None:
    agent = Agent(
        name="styled-agent",
        tools=[double],
        engine=PYTHON_RUNTIME_ENGINE,
        framework=STRANDS_FRAMEWORK,
    )

    result = agent.run({"value": 21}, mode="eval")
    node_state = agent.as_node(result_key="result")({"prompt": {"value": 21}})

    assert result.meta["framework"] == STRANDS_FRAMEWORK
    assert result.meta["framework_requested"] == STRANDS_FRAMEWORK
    assert result.meta["framework_adapter"] is None
    assert node_state["result"]["data"]["result"] == 42
    assert node_state["result"]["meta"]["framework_adapter"] is None
