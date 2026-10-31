"""Regressions for the audited 2.1.3 gaps; real Python execution, zero inference."""
from dataclasses import replace
import json
import random
import threading

import pytest
import agentic_systems as toolkit


@toolkit.tool
def decide(amount: int, *, context: toolkit.Context) -> dict:
    return {"decision": "review" if amount > context.data["threshold"] else "approve",
            "previous_episodes": len(context.episodes)}


def unit(backend="native", **kwargs):
    return toolkit.Agent("decision", toolkit.Action("decide", decide), backend=backend, **kwargs)


def assert_evidence(result):
    assert result.check_invariants().ok, result.check_invariants().to_dict()
    assert toolkit.RunResult(**json.loads(json.dumps(result.to_dict()))).to_dict() == result.to_dict()
    assert result.usage.get("inference_requests", 0) == 0


def test_context_snapshot_sources_redaction_and_identity():
    data = {"threshold": 100, "nested": {"currency": "MXN"}, "api_key": "fixture-secret"}
    context = toolkit.Context(data, sources=("policy-v3",))
    before = context.fingerprint
    data["nested"]["currency"] = "USD"
    context.data["nested"]["currency"] = "EUR"
    assert context.data["nested"]["currency"] == "MXN"
    assert context.fingerprint == before and context.sources == ("policy-v3",)
    assert "fixture-secret" not in json.dumps(context.to_dict())
    assert context.fingerprint == toolkit.Context(context.data, sources=context.sources).fingerprint


@pytest.mark.parametrize("data,sources", [([], ()), ({1: "bad"}, ()), ({"x": object()}, ()), ({"x": float("nan")}, ()), ({}, ["source"]), ({}, ("",))])
def test_context_rejects_nonportable_or_ambiguous_values(data, sources):
    with pytest.raises((ValueError, TypeError)):
        toolkit.Context(data, sources=sources)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_context_changes_decision_without_changing_business_input(backend):
    payload = {"amount": 75}
    low = unit(backend, context=toolkit.Context({"threshold": 50})).run(payload)
    high = unit(backend, context=toolkit.Context({"threshold": 100})).run(payload)
    assert low.data["decision"] == "review" and high.data["decision"] == "approve"
    assert payload == {"amount": 75}
    assert low.meta["context"]["fingerprint"] != high.meta["context"]["fingerprint"]
    for result in (low, high):
        assert_evidence(result)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_parallel_context_scopes_do_not_leak(backend):
    first = unit(backend, context=toolkit.Context({"threshold": 50}))
    second = replace(first, name="second", context=toolkit.Context({"threshold": 100}))
    target = toolkit.System("scopes", toolkit.Parallel((first, second), lambda rows: rows), backend=backend)
    for _ in range(3):
        result = target.run({"amount": 75})
        assert result.ok and result.data["decision"]["decision"] == "review"
        assert result.data["second"]["decision"] == "approve"
        assert_evidence(result)


def test_context_conflicts_are_visible_not_last_write_wins():
    target = toolkit.System("parent", unit(context=toolkit.Context({"threshold": 50})), context=toolkit.Context({"threshold": 100}))
    result = target.run({"amount": 75})
    assert not result.ok and "Conflicting Context key" in str(result.errors)
    assert_evidence(result)


def test_memory_reads_a_snapshot_then_remembers_outcome():
    memory = toolkit.Memory(capacity=2)
    worker = unit(context=toolkit.Context({"threshold": 100}), memory=memory)
    first, second, third = [worker.run({"amount": 75}) for _ in range(3)]
    assert [r.data["previous_episodes"] for r in (first, second, third)] == [0, 1, 2]
    entries = memory.read()
    assert [e["execution_id"] for e in entries] == [second.execution_id, third.execution_id]
    assert [e["revision"] for e in entries] == [2, 3]
    entries[0]["ok"] = False
    assert memory.read()[0]["ok"] is True
    memory.remember(third)
    assert len(memory.read()) == 2
    for result in (first, second, third):
        assert_evidence(result)


def test_memory_keeps_failures_without_asserting_their_conclusions():
    memory = toolkit.Memory()
    worker = toolkit.Agent("fail", toolkit.Action("raise", lambda d: (_ for _ in ()).throw(ValueError("controlled"))), memory=memory)
    failed = worker.run({})
    assert not failed.ok and memory.read()[0]["ok"] is False
    assert memory.read()[0]["lineage"]["failed_steps"] > 0
    assert_evidence(failed)


def test_compilation_never_reads_memory_or_starts_lazy_source(monkeypatch):
    memory = toolkit.Memory()
    def forbidden(*args):
        raise AssertionError("Compilation executed user behavior")
    monkeypatch.setattr(memory, "_snapshot", forbidden)
    worker = unit(context=toolkit.Context({"threshold": 100}), memory=memory)
    worker.compile().inspect()
    toolkit.Environment("source", worker, forbidden, stop=forbidden).compile().inspect()


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_nested_public_run_cannot_reset_shared_action_budget(backend):
    calls = []
    def operation(data):
        calls.append(True)
        return {"value": data["value"] + 1}
    child = toolkit.Agent("child", toolkit.Sequence((toolkit.Action("one", operation), toolkit.Action("two", operation))))
    target = toolkit.System("parent", toolkit.Sequence((toolkit.Action("delegate", child.run),)), backend=backend)
    result = target.run({"value": 0}, limits=toolkit.Limits(max_actions=1))
    assert not result.ok and not calls
    assert result.meta["actions_observed"] == 1
    assert "Shared action limit" in str(result.errors)
    assert_evidence(result)


def test_nested_run_cannot_request_a_larger_budget():
    child = toolkit.Agent("child", toolkit.Action("echo", lambda d: d))
    parent = toolkit.Agent("parent", toolkit.Action("delegate", lambda d: child.run(d, limits=toolkit.Limits(max_actions=500))))
    result = parent.run({})
    assert not result.ok and "Nested runs inherit limits" in str(result.errors)


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_python_actor_and_flow_keep_exact_tool_business_output(framework):
    @toolkit.tool
    def operation(value: int) -> dict:
        return {"value": value + 1, "ok": "business-field", "tool": "business-field", "data": {"nested": True}}
    flow = toolkit.Agent("flow", toolkit.Action("compute", operation))
    actor = toolkit.Agent("actor", runtime=toolkit.runtime(provider="python-runtime"), framework=toolkit.framework(framework),
                          skills=(toolkit.skill(name="compute", tools=(operation,)),))
    expected = flow.run({"value": 2})
    actual = actor.run({"value": 2})
    assert actual.ok and actual.data == expected.data
    assert_evidence(actual)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_input_output_schema_contract_applies_to_flow_and_system(backend):
    schema = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"], "additionalProperties": False}
    calls = []
    action = toolkit.Action("echo", lambda d: calls.append(True) or d)
    for owner in (toolkit.Agent, toolkit.System):
        worker = owner("typed", action, backend=backend, contract={"input_schema": schema, "output_schema": schema})
        good = worker.run({"value": 2})
        assert good.ok
        calls.clear()
        bad = worker.run({"value": "invalid"})
        assert not bad.ok and not calls
        assert_evidence(bad)
        wrong = replace(worker, flow=toolkit.Action("wrong", lambda d: {"value": "wrong"})).run({"value": 2})
        assert not wrong.ok and "output_schema_mismatch" in str(wrong.errors)


def test_symbolic_and_stochastic_python_are_not_language_model_reasoning():
    def draw(data):
        rng = random.Random(data["seed"])
        return {"sample": rng.random(), "eligible": data["amount"] >= 10}
    worker = toolkit.Agent("simulation", toolkit.Action("draw", draw))
    first = worker.run({"seed": 7, "amount": 12})
    again = worker.run({"seed": 7, "amount": 12})
    other = worker.run({"seed": 8, "amount": 12})
    assert first.data == again.data and first.data != other.data
    assert_evidence(first)


@pytest.mark.parametrize("budget", [80, 100, 160, 400, 1600])
def test_lineage_budget_returns_valid_json_and_explicit_omissions(budget):
    result = toolkit.RunResult(data={"huge": "x" * 10000}, ok=False, errors=({"code": "controlled"},))
    lineage = result.lineage()
    encoded = lineage.to_prompt_context(max_chars=budget)
    parsed = json.loads(encoded)
    assert len(encoded) <= budget and parsed["ok"] is False
    assert parsed["failed_steps"] > 0 and "omitted_steps" in parsed
    with pytest.raises(ValueError):
        lineage.to_prompt_context(max_chars=1)


def test_human_view_reports_late_failures_without_dumping_large_payload():
    children = tuple(toolkit.RunResult(data={"huge": "x" * 10000}, execution_id=f"step-{i}", parent_execution_id="root", ok=i != 18,
                                      errors=() if i != 18 else ({"code": "controlled"},)) for i in range(20))
    root = toolkit.RunResult(execution_id="root", children=children, ok=False)
    rendered = root.lineage().render()
    assert "FAILED" in rendered and "step-18" in rendered and len(rendered) < 5000
    trace = root.trace(max_steps=3)
    assert len(trace["steps"]) == 3 and trace["omitted_steps"] == 18
    assert any(s["execution_id"] == "step-18" for s in trace["steps"])


def test_memory_concurrent_writes_are_bounded_and_have_unique_revisions():
    memory = toolkit.Memory(capacity=5)
    threads = [threading.Thread(target=memory.remember, args=(toolkit.RunResult(data={"i": i}),)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    entries = memory.read()
    assert len(entries) == 5
    assert [e["revision"] for e in entries] == list(range(16, 21))


@pytest.mark.parametrize("capacity", [0, -1, True, 1.5])
def test_memory_capacity_is_a_positive_integer(capacity):
    with pytest.raises(ValueError):
        toolkit.Memory(capacity=capacity)


def test_context_injection_requires_explicit_type_and_keyword_only():
    def positional(context: toolkit.Context) -> dict:
        return {}
    def untyped(*, context) -> dict:
        return {}
    for operation in (positional, untyped):
        with pytest.raises(TypeError):
            toolkit.tool(operation)


def test_invalid_input_failure_is_recorded_in_memory_before_any_tool_call():
    memory = toolkit.Memory()
    schema = {"type": "object", "required": ["amount"], "properties": {"amount": {"type": "integer"}}}
    failed = unit(context=toolkit.Context({"threshold": 100}), memory=memory,
                  contract={"input_schema": schema}).run({"amount": "wrong"})
    assert not failed.ok and not any(n.tool_events for n in failed.walk())
    assert memory.read()[0]["execution_id"] == failed.execution_id and memory.read()[0]["ok"] is False
