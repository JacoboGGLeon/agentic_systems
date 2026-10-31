import json
import threading
import time

import pytest
from langgraph.graph import StateGraph, START, END

import agentic_systems as t
from test_graph_contracts import State, graph, assert_result


def test_context_is_detached_domain_information_not_mutable_graph_state():
    supplied = {"currency": "MXN", "factor": 2}
    context = t.Context(supplied, sources=("policy-v1",))
    supplied["factor"] = 9
    context.data["factor"] = 7
    assert context.data["factor"] == 2
    with pytest.raises((TypeError, ValueError)):
        t.Context({"bad": float("nan")})
    @t.tool
    def operation(value: int, *, context: t.Context) -> dict:
        return {"value": value * context.data["factor"], "info": context.to_dict()}
    memory = t.Memory()
    actor = t.Agent("context", graph(operation), context=context, memory=memory)
    first, second = actor.run({"value": 2}), actor.run({"value": 3})
    assert first.ok and first.data["value"] == 4 and not first.data["info"]["episodes"]
    assert second.ok and len(second.data["info"]["episodes"]) == 1
    assert memory.read()[0]["execution_id"] == first.execution_id
    assert_result(second)


def test_agents_receive_compact_preceding_lineage_and_inherit_context():
    @t.tool
    def contextual(value: int, *, context: t.Context) -> dict:
        return {"info": context.to_dict()}
    child = t.Agent("child", graph(contextual))
    b = StateGraph(State)
    b.add_node("before", lambda s: {"value": 8})
    b.add_node("child", child)
    b.add_edge(START, "before")
    b.add_edge("before", "child")
    b.add_edge("child", END)
    output = t.System("parent", b, context=t.Context({"currency": "MXN"}, sources=("policy",))).run({"value": 0})
    assert output.ok and output.data["info"]["data"] == {"currency": "MXN"}
    assert 1 <= len(output.data["info"]["lineage"]) <= 8
    assert all("children" not in row for row in output.data["info"]["lineage"])
    assert_result(output)


def test_conflicting_context_is_rejected_and_failures_are_remembered():
    child = t.Agent("child", graph(), context=t.Context({"currency": "USD"}))
    memory = t.Memory()
    output = t.System("parent", graph(child), context=t.Context({"currency": "MXN"}), memory=memory).run({"value": 1})
    assert not output.ok and "Conflicting Context" in str(output.errors)
    assert memory.read()[0]["ok"] is False
    assert_result(output)


@pytest.mark.parametrize("limit", [None, 1, 3, 10])
def test_environment_step_ceiling_is_not_padding(limit):
    output = t.Environment("episode", graph(), ({"value": 1}, {"value": 2}, {"value": 3}), max_steps=limit).run()
    count = 1 if limit == 1 else 3
    assert output.ok and output.data["summary"]["processed"] == count, output.to_dict()
    assert output.data["summary"]["reason"] == ("step_limit" if limit == 1 else "records_exhausted")
    assert len(output.data["history"]) == count and '"children"' not in json.dumps(output.data["history"])
    assert_result(output)


@pytest.mark.parametrize("limit", [0, -1, "inf", True, 2.5])
def test_environment_has_one_spelling_for_unbounded(limit):
    with pytest.raises(ValueError):
        t.Environment("episode", graph(), ({"value": 1},), max_steps=limit).compile()


def test_lazy_environment_pauses_without_reconsuming_or_closing():
    seen, closed = [], []
    def source():
        try:
            for i in range(2):
                seen.append(i)
                yield {"value": i}
        finally:
            closed.append(True)
    b = graph(lambda s: {"approved": t.pause({"value": s["value"]})})
    program = t.Environment("pause", b, source).compile()
    assert not seen
    first = program.run()
    assert first.status == "paused" and seen == [0] and not closed, first.to_dict()
    second = program.resume(first, True)
    assert second.status == "paused" and seen == [0, 1] and not closed, second.to_dict()
    final = program.resume(second, False)
    assert final.ok and final.data["summary"]["processed"] == 2 and closed == [True], final.to_dict()
    assert_result(final)


def test_lazy_source_closes_at_ceiling_without_extra_read():
    seen, closed = [], []
    def source():
        try:
            for i in range(10):
                seen.append(i)
                yield {"value": i}
        finally:
            closed.append(True)
    output = t.Environment("stream", graph(), source, max_steps=2).run()
    assert output.ok and seen == [0, 1] and closed == [True]


def test_unbounded_environment_still_obeys_root_limits():
    def source():
        while True:
            yield {"value": 1}
    output = t.Environment("stream", graph(), source).run(timeout_s=0.05)
    assert not output.ok and output.meta['nodes_observed'] > 0
    assert output.data["summary"]["reason"] == "execution_limit"
    assert_result(output)


def test_environment_context_state_and_stop():
    @t.tool
    def multiply(value: int, *, context: t.Context) -> dict:
        return {"value": value * context.data["factor"]}
    episode = t.Environment("state", graph(multiply), tuple({"value": i} for i in range(1, 10)),
        context=t.Context({"factor": 2}), state={"total": 0},
        update=lambda state, row, result: {"total": state["total"] + result.data["value"]},
        stop=lambda state, result: state["total"] >= 6)
    output = episode.run()
    assert output.ok and output.data["summary"]["state"] == {"total": 6}
    assert output.data["summary"]["reason"] == "stop"


def test_eval_expected_failure_and_no_pause():
    def fail(s):
        raise ValueError("controlled failure")
    evaluation = t.Eval("expected-failure", t.Agent("fail", graph(fail)),
        ({"input": {}, "expected": {"ok": False}},)).run()
    assert evaluation.ok and evaluation.data["passed"] == 1, evaluation.to_dict()
    assert_result(evaluation)
    interrupted = t.Eval("no-pause", t.Agent("a", graph(lambda s: {"approved": t.pause({})})),
        ({"input": {"value": 1}, "expected": {"ok": True}},)).run()
    assert not interrupted.ok and "outside actors and Eval" in str(interrupted.errors)


def test_eval_references_results_instead_of_copying_them_into_rows():
    episode = t.Environment("state", graph(), ({"value": 1},))
    output = t.Eval("episode-eval", episode, ({"input": {"records": [{"value": 4}]}, "expected": {"ok": True}},),
        checks=(lambda r, c: {"ok": r.data["outputs"] == [{"value": 5}]},)).run()
    assert output.ok and output.data["passed"] == 1, output.to_dict()
    assert "result" not in output.data["cases"][0] and "execution_id" in output.data["cases"][0]
    assert_result(output)


def test_concurrent_sibling_is_not_in_contextual_predecessor_lineage():
    ready = threading.Event()
    @t.tool
    def inspect_context(value: int, *, context: t.Context) -> dict:
        return {"info": context.to_dict()}
    child = t.Agent("inspect", graph(inspect_context))
    def left(state):
        ready.set()
        return {"left": 1}
    def right(state):
        assert ready.wait(2)
        time.sleep(0.03)
        return child.run(state)
    b = StateGraph(State)
    b.add_node("before", lambda s: {"value": 2})
    b.add_node("left", left)
    b.add_node("right", right)
    b.add_edge(START, "before")
    b.add_edge("before", "left")
    b.add_edge("before", "right")
    b.add_edge("left", END)
    b.add_edge("right", END)
    output = t.System("concurrent-context", b).run({"value": 1})
    assert output.ok, output.to_dict()
    names = {row["name"] for row in output.data["info"]["lineage"]}
    assert "before" in names and "left" not in names


def test_plain_langgraph_node_receives_the_same_public_context_via_runtime():
    def contextual(state, *, context: t.Context):
        return {"value": state["value"] * context.data["factor"], "info": context.to_dict()}
    b = StateGraph(State, context_schema=t.Context)
    b.add_node("before", lambda s: {"value": 3})
    b.add_node("read_context", contextual)
    b.add_edge(START, "before")
    b.add_edge("before", "read_context")
    b.add_edge("read_context", END)
    output = t.Agent("runtime-context", b, context=t.Context({"factor": 2}, sources=("policy",))).run({"value": 0})
    assert output.ok and output.data["value"] == 6, output.to_dict()
    assert output.data["info"]["sources"] == ["policy"]
    assert output.data["info"]["lineage"][0]["name"] == "before"
