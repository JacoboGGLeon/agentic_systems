"""Owner composition, rejected SDK policies and resume evidence contracts."""

import runpy
import sys

import pydantic
import pytest
from langgraph.types import CachePolicy, RetryPolicy
from typing_extensions import TypedDict

import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: int


def keep(state):
    return {"value": state.value}


def graph(operation=keep, **options):
    builder = toolkit.Graph(State)
    builder.add_node("work", operation, **options)
    builder.add_edge(toolkit.START, "work")
    builder.add_edge("work", toolkit.END)
    return builder


@pytest.mark.parametrize("options,error", [
    ({"instructions": 3}, TypeError),
    ({"runtime": toolkit.runtime(provider="openai-runtime")}, ValueError),
    ({"skills": []}, TypeError),
])
def test_invalid_agent_options_do_not_materialize_clients(options, error):
    selected = {"runtime": toolkit.runtime(provider="python-runtime")}
    if "skills" not in options:
        @toolkit.tool
        def operation(value: int) -> dict:
            return {"value": value}
        selected["skills"] = (toolkit.skill(name="work", tools=(operation,)),)
    with pytest.raises(error):
        toolkit.Agent("invalid", **{**selected, **options}).compile()


def test_duplicate_capabilities_and_actor_options_on_graph_are_rejected():
    @toolkit.tool
    def operation(value: int) -> dict:
        return {"value": value}

    skill = toolkit.skill(name="work", tools=(operation,))
    with pytest.raises(ValueError, match="Duplicate Tool"):
        toolkit.Agent("duplicates", runtime=toolkit.runtime(provider="python-runtime"), skills=(skill, skill)).compile()
    with pytest.raises(ValueError, match="Actor SDK options"):
        toolkit.Agent("graph", graph(), framework=toolkit.framework("strands")).compile()
    with pytest.raises(ValueError, match="Graph contracts"):
        toolkit.System("graph", graph(), contract={"completion": "always_finalize"}).compile()


@pytest.mark.parametrize("options", [{"cache_policy": CachePolicy()}, {"retry_policy": RetryPolicy()}])
def test_sdk_execution_policies_cannot_skip_or_duplicate_toolkit_evidence(options):
    with pytest.raises(ValueError):
        toolkit.System("unsupported", graph(**options)).compile()


def test_graph_context_and_reserved_state_are_checked():
    builder = toolkit.Graph(State, context_schema=dict)
    builder.add_node("work", keep)
    builder.add_edge(toolkit.START, "work")
    builder.add_edge("work", toolkit.END)
    with pytest.raises(ValueError, match="toolkit.Context"):
        toolkit.System("wrong-context", builder).compile()

    class Reserved(TypedDict):
        value: int
        _lineage: list

    with pytest.raises(ValueError, match="reserved"):
        toolkit.System("reserved", toolkit.Graph(Reserved)).compile()


def test_resume_does_not_repeat_completed_tools_or_owner_calls():
    calls = []

    def increment(state):
        calls.append(state.value)
        return {"value": state.value + 1}

    worker = toolkit.Agent("worker", graph(increment))

    def approval(state):
        toolkit.pause({"value": state.value})
        return {"value": state.value}

    builder = toolkit.Graph(State)
    builder.add_node("worker", worker)
    builder.add_node("approval", approval)
    builder.add_edge(toolkit.START, "worker")
    builder.add_edge("worker", "approval")
    builder.add_edge("approval", toolkit.END)
    program = toolkit.System("review", builder).compile()
    paused = program.run({"value": 3})
    assert paused.status == "paused" and calls == [3]
    resumed = program.resume(paused, True)
    assert resumed.ok and resumed.data == {"value": 4} and calls == [3]
    assert worker({"value": 5}) == {"value": 6}


def test_cli_module_entrypoint_and_framework_option_serialization(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["agentic-systems", "version"])
    with pytest.raises(SystemExit) as result:
        runpy.run_module("agentic_systems.cli", run_name="__main__")
    assert result.value.code == 0 and toolkit.__version__ in capsys.readouterr().out
    config = toolkit.framework("openai-agents", agent_kwargs={"model_settings": {"reasoning": {"effort": "low"}}})
    assert config.inspect()["name"] == "openai-agents"


def test_provider_contracts_preserve_forbidden_evidence_and_allowed_failures(monkeypatch):
    @toolkit.tool
    def operation(value: int) -> dict:
        return {"value": value}

    skill = toolkit.skill(name="work", tools=(operation,))
    raw = toolkit.RunResult(data={"value": 3}, tool_events=({"id": "tool", "name": "operation", "input": {}, "output": {}},))
    monkeypatch.setattr("agentic_systems._grammar._invoke_actor", lambda *args: raw)
    forbidden = toolkit.Agent("forbidden", runtime=toolkit.runtime(provider="python-runtime"), skills=(skill,),
                              contract={"tool_expectation": {"forbidden": ["operation"]}}).run({"value": 3})
    assert not forbidden.ok and "forbidden_tool" in str(forbidden.errors)
    allowed = toolkit.Agent("allowed", runtime=toolkit.runtime(provider="python-runtime"), skills=(skill,),
                            contract={"failure_policy": "allow"}).run({"value": 3})
    assert allowed.ok and allowed.check_invariants().ok
    for policy, contract in [({"tool_choice": "none"}, {"tool_expectation": {"all_of": ["operation"]}}),
                              ({"finalize": "never"}, {"completion": "always_finalize"})]:
        with pytest.raises(ValueError):
            toolkit.Agent("conflict", runtime=toolkit.runtime(provider="python-runtime"), skills=(skill,),
                          policy=policy, contract=contract).compile()


def test_recursive_owner_definitions_fail_instead_of_building_unbounded_graphs():
    owner = toolkit.System("recursive", graph())
    builder = graph(owner)
    object.__setattr__(owner, "graph", builder)
    with pytest.raises(ValueError, match="Recursive"):
        owner.compile()


def test_untyped_graph_state_is_rejected_before_execution():
    with pytest.raises(TypeError, match="Pydantic or TypedDict"):
        toolkit.System("untyped", toolkit.Graph(dict)).compile()


@pytest.mark.parametrize("update", [[], {"_lineage": ["forged-evidence"]}])
def test_nodes_cannot_return_nonmapping_updates_or_forge_lineage(update):
    def invalid(state):
        return update

    result = toolkit.Agent("invalid-update", graph(invalid)).run({"value": 3})
    assert not result.ok and "_lineage is managed internally" in str(result.errors)
