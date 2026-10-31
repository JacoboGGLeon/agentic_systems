"""Fault injection at SDK boundaries must preserve control, evidence and cleanup."""

from types import SimpleNamespace

import pydantic
import pytest
from langgraph.types import Interrupt

import agentic_systems as toolkit
from agentic_systems._grammar import _ExecutionContext


class State(pydantic.BaseModel):
    value: int


def graph(operation):
    builder = toolkit.Graph(State)
    builder.add_node("work", operation)
    builder.add_edge(toolkit.START, "work")
    builder.add_edge("work", toolkit.END)
    return builder


def keep(state):
    return {"value": state.value}


def test_sdk_failure_closes_owned_iterators_and_keeps_failure_status(monkeypatch):
    closed = []
    program = toolkit.Agent("cleanup", graph(keep)).compile()

    def interrupted(*args, **kwargs):
        root = kwargs["context"]["execution"]
        root.sources["owned"] = SimpleNamespace(close=lambda: closed.append(True))
        assert root.scoped(toolkit.Context({})).nodes == root.nodes
        raise RuntimeError("SDK invocation aborted")

    monkeypatch.setattr(program._driver.graph, "invoke", interrupted)
    result = program.run({"value": 3})
    assert not result.ok and "SDK invocation aborted" in str(result.errors)
    assert closed == [True]


def test_returned_sdk_interrupt_is_not_reported_as_completed(monkeypatch):
    program = toolkit.Agent("interrupt", graph(keep)).compile()
    monkeypatch.setattr(program._prepared.native, "invoke", lambda *args, **kwargs: {
        "value": 3, "__interrupt__": (Interrupt(value={"approval": True}, id="sdk-interrupt"),)})
    result = program.run({"value": 3})
    assert result.status == "paused" and result.interrupts


def test_nested_pause_replays_python_callback_without_repeating_child_work():
    calls = []

    def work(state):
        calls.append(state.value)
        return {"value": state.value + 1}

    child = toolkit.Agent("child", graph(work)).compile()

    def parent(state):
        completed = child.run({"value": state.value})
        toolkit.pause({"value": completed.data["value"]})
        return completed.data

    program = toolkit.System("parent", graph(parent)).compile()
    waiting = program.run({"value": 3})
    assert waiting.status == "paused"
    finished = program.resume(waiting, True)
    assert finished.ok and calls == [3] and finished.data == {"value": 4}


def test_compiled_native_graph_cannot_be_executed_without_toolkit_scope():
    program = toolkit.Agent("owned", graph(keep)).compile()
    with pytest.raises(RuntimeError, match="through its Agent"):
        program._prepared.native.invoke({"value": 3})


def test_replayed_graph_segment_preserves_results_without_repeating_effects():
    calls = []

    def operation(state):
        calls.append(state.value)
        return {"value": state.value + 1}

    prepared = toolkit.Agent("replayed", graph(operation)).compile()._prepared
    context = _ExecutionContext()
    first = prepared.execute({"value": 3}, context)
    replayed = prepared.execute({"value": 3}, context)
    assert first.ok and replayed.ok and first.data == replayed.data == {"value": 4}
    assert calls == [3]


def test_provider_evidence_is_reparented_and_false_success_is_rejected(monkeypatch):
    from agentic_systems._engine.results import RunResult as EngineResult

    child = EngineResult(data={"value": 3})
    external = EngineResult(data={"value": 3}, children=(child,))
    monkeypatch.setattr("agentic_systems._engine.factories.agent", lambda **kwargs: SimpleNamespace(run=lambda value: external))

    @toolkit.tool
    def operation(value: int) -> dict:
        return {"value": value}

    actor = toolkit.Agent("actor", runtime=toolkit.runtime(provider="python-runtime"),
                          skills=(toolkit.skill(name="work", tools=(operation,)),))
    valid = actor.run({"value": 3})
    assert valid.ok and valid.check_invariants().ok
    invalid = toolkit.RunResult(data={"value": 3}, usage={"input_tokens": -1})
    monkeypatch.setattr("agentic_systems._grammar._invoke_actor", lambda *args: invalid)
    rejected = actor.run({"value": 3})
    assert not rejected.ok and "invariant_failed" in str(rejected.errors)


def test_explicitly_allowed_provider_errors_keep_their_evidence(monkeypatch):
    raw = toolkit.RunResult(data={"value": 3}, errors=({"code": "handled-error"},))
    monkeypatch.setattr("agentic_systems._grammar._invoke_actor", lambda *args: raw)

    @toolkit.tool
    def operation(value: int) -> dict:
        return {"value": value}

    actor = toolkit.Agent("allowed", runtime=toolkit.runtime(provider="python-runtime"),
                          skills=(toolkit.skill(name="work", tools=(operation,)),),
                          contract={"failure_policy": "allow"})
    result = actor.run({"value": 3})
    assert result.ok and result.errors and result.check_invariants().ok
    assert result.meta["allowed_error_ids"]


def test_pause_transport_failure_is_a_failure_not_a_continuation(monkeypatch):
    def unavailable(value):
        raise RuntimeError("SDK interrupt transport failed")

    def approval(state):
        toolkit.pause({"value": state.value})
        return {"value": state.value}

    monkeypatch.setattr("langgraph.types.interrupt", unavailable)
    result = toolkit.Agent("approval", graph(approval)).run({"value": 3})
    assert not result.ok and result.status == "failed"
    assert "SDK interrupt transport failed" in str(result.errors)


def test_late_actor_output_keeps_usage_and_data_after_root_deadline(monkeypatch):
    from agentic_systems._context import _active_execution

    @toolkit.tool
    def operation(value: int) -> dict:
        return {"value": value}

    def late_response(*args):
        root = _active_execution.get()
        while hasattr(root, "parent"):
            root = root.parent
        root.started -= 60
        return toolkit.RunResult(data={"value": 7}, usage={"inference_requests": 1})

    monkeypatch.setattr("agentic_systems._grammar._invoke_actor", late_response)
    result = toolkit.Agent("late", runtime=toolkit.runtime(provider="python-runtime"),
                           skills=(toolkit.skill(name="work", tools=(operation,)),)).run({"value": 3}, timeout_s=30)
    assert not result.ok and result.usage["inference_requests"] == 1
    assert any(row.data == {"value": 7} for row in result.walk())


def test_dynamic_callable_owner_and_nested_pause_keep_the_same_execution():
    def approval(state):
        answer = toolkit.pause({"value": state.value})
        return {"value": state.value + int(answer)}

    child = toolkit.Agent("child", graph(approval))

    def invoke(state):
        return child(state)

    program = toolkit.System("dynamic", graph(invoke)).compile()
    waiting = program.run({"value": 3})
    assert waiting.status == "paused"
    final = program.resume(waiting, True)
    assert final.ok and final.data == {"value": 4}


def test_sdk_graph_interrupt_bubbles_without_becoming_a_business_error():
    from langgraph.errors import GraphInterrupt

    def control(state):
        raise GraphInterrupt((Interrupt(value={"value": state.value}, id="native-control"),))

    waiting = toolkit.System("sdk-control", graph(control)).run({"value": 3})
    assert waiting.status == "paused" and not waiting.errors


def test_node_context_requires_the_toolkit_contract():
    def wrong(state, *, context: dict):
        return {"value": state.value}

    with pytest.raises(TypeError, match="toolkit.Context"):
        toolkit.System("wrong-context", graph(wrong)).compile()


def test_environment_compilation_reuses_ownership_without_consuming_records():
    consumed = []

    def records():
        consumed.append(True)
        yield {"value": 3}

    environment = toolkit.Environment("lazy", graph(keep), records)
    registry = {}
    prepared = environment._compile(set(), registry)
    assert environment._compile(set(), registry) is prepared and not consumed
    with pytest.raises(ValueError, match="Recursive Environment"):
        environment._compile({id(environment)}, {})
