import asyncio
from dataclasses import replace
import json
import operator
import time
from typing import Annotated

import pytest
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing_extensions import TypedDict

import agentic_systems as t


class State(TypedDict, total=False):
    value: int
    left: int
    right: int
    approved: bool
    info: dict


def graph(operation=lambda s: {"value": s["value"] + 1}):
    builder = StateGraph(State)
    builder.add_node("work", operation)
    builder.add_edge(START, "work")
    builder.add_edge("work", END)
    return builder


def assert_result(output):
    assert output.check_invariants().ok, output.check_invariants().to_dict()
    assert json.loads(json.dumps(output.to_dict()))["status"] == output.status


def test_one_engine_one_graph_grammar():
    assert len(set(t.__all__) - {"__version__", "Graph", "START", "END", "Command", "Send"}) == 15
    for word in ("Sequence", "Parallel", "StateGraph", "check"):
        assert not hasattr(t, word)
    with pytest.raises(TypeError):
        t.Agent("bad", graph(), backend="native")
    with pytest.raises(TypeError):
        t.Agent("bad", flow=graph())
    with pytest.raises(ValueError, match="orchestration"):
        t.framework("langgraph")


@pytest.mark.parametrize("owner", [t.Agent, t.System])
def test_compile_is_pure_and_reusable(owner):
    calls = []
    def work(s):
        calls.append(1)
        return {"value": s["value"] + 1}
    program = owner("one", graph=graph(work)).compile()
    assert not calls and program.inspect()["graph"]["engine"] == "langgraph"
    assert program.run({"value": 1}).data == {"value": 2}
    assert asyncio.run(program.arun({"value": 2})).data == {"value": 3}
    assert len(calls) == 2


@pytest.mark.parametrize("owner", [t.Agent, t.System])
def test_parallel_disjoint_updates_and_langgraph_barrier(owner):
    completed = []
    b = StateGraph(State)
    b.add_node("left", lambda s: {"left": s["value"] + 1})
    b.add_node("right", lambda s: {"right": s["value"] * 2})
    def total(s):
        completed.append((s["left"], s["right"]))
        return {"value": s["left"] + s["right"]}
    b.add_node("total", total)
    b.add_edge(START, "left")
    b.add_edge(START, "right")
    b.add_edge(["left", "right"], "total")
    b.add_edge("total", END)
    output = owner("parallel", graph=b).run({"value": 2})
    assert output.ok and output.data["value"] == 7 and completed == [(3, 4)], output.to_dict()
    assert_result(output)


def test_standard_langgraph_reducer_and_conflicting_writes():
    class Reduced(TypedDict):
        values: Annotated[list[int], operator.add]
    b = StateGraph(Reduced)
    for name, value in (("a", 1), ("b", 2)):
        b.add_node(name, lambda s, value=value: {"values": [value]})
        b.add_edge(START, name)
        b.add_edge(name, END)
    output = t.System("reduce", b).run({"values": []})
    assert output.ok and sorted(output.data["values"]) == [1, 2], output.to_dict()
    bad = StateGraph(State)
    for name in ("a", "b"):
        bad.add_node(name, lambda s: {"value": 1})
        bad.add_edge(START, name)
        bad.add_edge(name, END)
    assert not t.System("conflict", bad).run({"value": 0}).ok


@pytest.mark.parametrize("value,expected", [(0, 6), (-3, -2)])
def test_decision_and_nested_agent(value, expected):
    b = StateGraph(State)
    b.add_node("increase", t.Agent("incrementer", graph()))
    b.add_node("double", lambda s: {"value": s["value"] * 6})
    b.add_edge(START, "increase")
    b.add_conditional_edges("increase", lambda s: "double" if s["value"] >= 0 else END, ["double", END])
    b.add_edge("double", END)
    output = t.System("decision", b).run({"value": value})
    assert output.ok and output.data["value"] == expected, output.to_dict()
    assert any(n.meta.get("kind") == "agent" for n in output.walk())
    assert_result(output)


def test_command_and_async_nodes():
    b = StateGraph(State)
    b.add_node("route", lambda s: Command(update={"value": 2}, goto="async"), destinations=("async",))
    async def asynchronous(s):
        return {"value": s["value"] + 3}
    b.add_node("async", asynchronous)
    b.add_edge(START, "route")
    b.add_edge("async", END)
    output = asyncio.run(t.Agent("async", b).arun({"value": 0}))
    assert output.ok and output.data["value"] == 5, output.to_dict()


def test_output_schema_filters_private_input_fields():
    class Input(TypedDict):
        value: int
    class Output(TypedDict):
        left: int
    b = StateGraph(State, input_schema=Input, output_schema=Output)
    b.add_node("work", lambda s: {"left": s["value"] + 1})
    b.add_edge(START, "work")
    b.add_edge("work", END)
    output = t.Agent("project", b).run({"value": 2})
    assert output.ok and output.data == {"left": 3}


def approve(s):
    return {"approved": t.pause({"value": s["value"]})}


def test_pause_resume_preserves_context_memory_usage_and_completed_effects():
    calls, memory = [], t.Memory()
    def before(s):
        calls.append(1)
        return t.RunResult(data={"value": s["value"] + 1}, usage={"inference_requests": 1})
    b = StateGraph(State)
    b.add_node("before", before)
    b.add_node("approve", approve)
    b.add_edge(START, "before")
    b.add_edge("before", "approve")
    b.add_edge("approve", END)
    program = t.Agent("approval", b, context=t.Context({"policy": "v1"}), memory=memory).compile()
    waiting = program.run({"value": 2}, timeout_s=None)
    assert waiting.status == "paused" and memory.read() == [], waiting.to_dict()
    assert waiting.usage["inference_requests"] == 1
    for checkpoint in program._driver.saver.list({"configurable": {"thread_id": waiting.continuation["session"]}}):
        encoded = json.dumps(checkpoint.checkpoint["channel_values"])
        assert '"children"' not in encoded and '"raw_responses"' not in encoded
    final = program.resume(t.RunResult(**waiting.to_dict()), True)
    assert final.ok and final.data == {"value": 3, "approved": True} and calls == [1]
    assert final.meta['nodes_observed'] == 2 and final.usage["inference_requests"] == 1
    assert len(memory.read()) == 1
    assert_result(final)
    with pytest.raises(ValueError, match="completed"):
        program.resume(waiting, True)


def test_multiple_pauses_and_wrong_program_handles():
    b = StateGraph(State)
    b.add_node("a", approve)
    b.add_node("b", approve)
    b.add_edge(START, "a")
    b.add_edge("a", "b")
    b.add_edge("b", END)
    owner = t.Agent("two", b)
    program, other = owner.compile(), owner.compile()
    first = program.run({"value": 1})
    with pytest.raises(ValueError, match="another compiled"):
        other.resume(first, True)
    second = program.resume(first, True)
    assert second.status == "paused"
    with pytest.raises(ValueError, match="stale"):
        program.resume(first, True)
    final = asyncio.run(program.aresume(second, False))
    assert final.ok and final.data["approved"] is False


def test_deadline_excludes_human_wait():
    program = t.Agent("wait", graph(approve)).compile()
    waiting = program.run({"value": 0}, timeout_s=0.7)
    assert waiting.status == "paused"
    time.sleep(0.75)
    assert program.resume(waiting, True).ok


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limits_and_capacity(limit):
    with pytest.raises((ValueError, TypeError)):
        t.Memory(capacity=limit)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object()])
def test_non_json_input_returns_failure(value):
    output = t.Agent("json", graph()).run({"value": value})
    assert not output.ok


def test_nested_runs_cannot_reset_limits_and_failure_is_not_success():
    inner = t.Agent("inner", graph())
    outer = t.System("outer", graph(lambda s: inner.run(s, timeout_s=1)))
    output = outer.run({"value": 1})
    assert not output.ok and "inherit" in str(output.errors)
    assert_result(output)


def test_long_loop_state_keeps_only_bounded_ids_and_no_results():
    b = StateGraph(State)
    b.add_node("count", lambda s: {"value": s["value"] + 1})
    b.add_edge(START, "count")
    b.add_conditional_edges("count", lambda s: "count" if s["value"] < 80 else END, ["count", END])
    output = t.Agent("long", b).run({"value": 0}, timeout_s=30)
    assert output.ok and output.data["value"] == 80, output.to_dict()
    assert output.meta["state_metrics"]["max_lineage_refs"] == 32
    assert output.meta["state_metrics"]["max_bytes"] < 2000
    assert len(output.meta["lineage_refs"]) == 80
    assert_result(output)


def test_compile_rejects_reserved_channels_and_uncompiled_contract():
    class Reserved(TypedDict):
        _lineage: list
    with pytest.raises(ValueError, match="reserved"):
        t.Agent("bad", StateGraph(Reserved)).compile()
    with pytest.raises(TypeError):
        t.Agent("bad", graph().compile()).compile()
    with pytest.raises(ValueError):
        t.Agent("bad")


def test_graph_contract_failure_preserves_evidence():
    output = t.Agent("schema", graph(), contract={"output_schema": {"type": "object", "required": ["missing"]}}).run({"value": 2})
    assert not output.ok and output.children and "output_schema_mismatch" in str(output.errors)
    assert_result(output)


def test_declared_graph_is_not_mutated_by_compile():
    b = graph()
    before = b.nodes["work"].runnable
    definition = t.Agent("stable", b)
    assert definition.compile().run({"value": 2}).ok
    assert b.nodes["work"].runnable is before and "_lineage" not in b.channels
    assert replace(definition, name="again").run({"value": 1}).ok


def test_large_evidence_is_preserved_outside_all_checkpoint_channels():
    marker = "EVIDENCE_ONLY_" + "X" * 10000
    b = StateGraph(State)
    b.add_node("evidence", lambda s: t.RunResult(data={"value": 2}, raw_responses=({"payload": marker},)))
    b.add_node("approval", approve)
    b.add_edge(START, "evidence")
    b.add_edge("evidence", "approval")
    b.add_edge("approval", END)
    program = t.Agent("separate-evidence", b).compile()
    waiting = program.run({"value": 1})
    assert waiting.status == "paused"
    context = program._driver.sessions[waiting.continuation["session"]]["context"]
    assert marker in json.dumps(context.evidence.records)
    for checkpoint in program._driver.saver.list({"configurable": {"thread_id": waiting.continuation["session"]}}):
        state = json.dumps(checkpoint.checkpoint["channel_values"])
        assert marker not in state and '"raw_responses"' not in state and '"children"' not in state
    final = program.resume(waiting, True)
    assert final.ok and marker in json.dumps(final.to_dict())


def test_python_multi_tool_orchestration_requires_explicit_graph():
    @t.tool
    def first(value: int) -> dict:
        return {"value": value}
    @t.tool
    def second(value: int) -> dict:
        return {"value": value}
    with pytest.raises(ValueError, match="multi-tool"):
        t.Agent("bad", runtime=t.runtime(provider="python-runtime"),
                skills=(t.skill(name="multiple", tools=(first, second)),)).compile()


@pytest.mark.parametrize("kind", ["agent", "system", "environment", "eval"])
def test_all_execution_boundaries_require_a_readable_name(kind):
    owners = {"agent": t.Agent("", graph()), "system": t.System("", graph()),
              "environment": t.Environment("", graph(), ({"value": 1},)),
              "eval": t.Eval("", t.Agent("unit", graph()), ({"input": {"value": 1}, "expected": {"ok": True}},))}
    with pytest.raises(ValueError, match="name"):
        owners[kind].compile()
