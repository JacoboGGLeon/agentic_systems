from dataclasses import replace
import math

import pytest
import agentic_systems as a
from test_grammar import unit, assert_result


@pytest.mark.parametrize("policy", [{"max_turns": 10}, {"max_tool_calls": 1}, {"max_tokens": 20}, {"temperature": -1},
    {"tool_choice": "alias"}, {"repair": 1}, {"max_repairs": -1}, {"finalize": "alias"}, {"trace": "alias"}, {"strict": "yes"}])
def test_closed_policy_and_single_actor_budget(policy):
    with pytest.raises((ValueError, TypeError)):
        a.Agent("model", runtime=a.runtime(provider="openai-runtime", model="fixture"), policy=policy).compile()


@pytest.mark.parametrize("changes", [{"name": ""}, {"unit": object()}, {"records": ()}, {"records": []}, {"max_steps": 0}, {"max_steps": True},
    {"observe": "alias"}, {"update": "alias"}, {"stop": "alias"}])
def test_episode_configuration_validation(changes):
    with pytest.raises((ValueError, TypeError)):
        replace(a.Environment("episode", unit(), ({"value": 1},)), **changes).compile()


@pytest.mark.parametrize("changes", [{"name": ""}, {"unit": object()}, {"cases": ()}, {"cases": []}, {"checks": []},
    {"checks": (1,)}, {"judge": object()}, {"rubric": {"threshold": 0.5}}])
def test_evaluation_configuration_validation(changes):
    with pytest.raises((ValueError, TypeError)):
        replace(a.Eval("eval", unit(), ({"input": {"value": 1}, "expected": {"ok": True}},)), **changes).compile()


@pytest.mark.parametrize("rubric", [{"threshold": -1}, {"criteria": []}, {"criteria": ["x", "x"]}, {"instructions": 1},
    {"certification_tool": 1}, {"require_failure_findings": 1}, {"deterministic_authority": ["x"]}])
def test_judge_rubric_is_closed_and_typed(rubric):
    judge = a.Agent("judge", a.Action("score", lambda d: {}))
    with pytest.raises((ValueError, TypeError)):
        a.Eval("eval", unit(), ({"input": {"value": 1}},), judge=judge, rubric=rubric).compile()


@pytest.mark.parametrize("value", [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_tool_outputs_fail_with_evidence(value):
    @a.tool
    def invalid() -> dict:
        return {"value": value}
    result = invalid.run({})
    assert not result.ok and "non-finite" in str(result.errors)
    assert_result(result)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_optional_flow_names_nested_systems_and_explicit_failure(backend):
    nested = a.System("nested", a.Sequence((unit(backend),), name="named_sequence"), backend=backend)
    outer = a.System("outer", a.Parallel((nested,), join=lambda rows: rows["nested"], name="named_parallel"), backend=backend)
    result = outer.run({"value": 3})
    assert result.ok and result.data == {"value": 8}
    assert {n.meta.get("name") for n in result.walk()} >= {"named_sequence", "named_parallel", "nested", "outer"}
    assert_result(result)
    bad = a.Agent("bad", a.Parallel((a.Action("a", lambda d: d),), join=lambda rows: (_ for _ in ()).throw(ValueError("bad join"))), backend=backend).run({"value": 1})
    assert not bad.ok and any(n.ok for n in bad.walk())
    assert_result(bad)


def test_callback_failures_judge_certification_and_no_vacuous_acceptance():
    target = unit()
    for callback in (lambda result, case: {"ok": "true"}, lambda result, case: {"ok": True, "ignored": True},
                     lambda result, case: (_ for _ in ()).throw(RuntimeError("controlled check failure"))):
        result = a.Eval("bad_check", target, ({"input": {"value": 1}},), checks=(callback,)).run()
        assert not result.ok and result.children[0].ok
        assert_result(result)
    judge = a.Agent("fixture", a.Action("score", lambda d: {"criteria": {"correctness": 1.0}, "findings": []}))
    result = a.Eval("certification", target, ({"input": {"value": 1}},), judge=judge,
                    rubric={"criteria": ["correctness"], "certification_tool": "absent"}).run()
    assert not result.ok and not result.data["cases"][0]["judge"]["certification_recorded"]


def test_runtime_budget_forwarding_is_lossless(monkeypatch):
    import agentic_systems._engine.factories as implementation
    from agentic_systems._engine.results import RunResult
    observed = []
    class Actor:
        def run(self, input):
            return RunResult(data={"value": 1}, engine="openai-runtime", model="fixture")
    def factory(**kwargs):
        observed.append(kwargs)
        return Actor()
    monkeypatch.setattr(implementation, "agent", factory)
    config = a.runtime(provider="openai-runtime", model="fixture", endpoint="https://fixture.invalid", api_key="fixture-secret",
        timeout_s=17, max_retries=2, max_tool_calls=3, max_turns=9, max_tokens=127, backoff_s=0.2, max_concurrency=2)
    a.Agent("model", runtime=config, framework=a.framework("openai-agents", run_kwargs={"context": {"model": "application-data"}})).run({})
    private = observed[0]["runtime"]
    for key in ("timeout_s", "max_retries", "max_tool_calls", "max_turns", "backoff_s", "max_concurrency"):
        assert getattr(private.scheduler, key) == getattr(config, key)
    assert observed[0]["policy"]["max_tokens"] == 127
    assert observed[0]["framework"].run_kwargs == {"context": {"model": "application-data"}}
    with pytest.raises(ValueError):
        a.framework("openai-agents", agent_kwargs={"model_settings": {"max_tokens": 999}})
    with pytest.raises(ValueError):
        a.framework("native", agent_kwargs={"ignored": True})
    with pytest.raises(ValueError):
        a.framework("langgraph", run_kwargs={"ignored": True})


def test_result_all_fields_and_inconsistent_imports():
    child = a.RunResult(data={"value": 1}, execution_id="child", parent_execution_id="parent")
    event = {"id": "event", "name": "tool", "input": {"value": 0}, "output": {"value": 1}, "ok": True,
             "error": None, "duration_ms": 0.1, "meta": {"fixture": True}}
    result = a.RunResult(text="one", final={"summary": "one"}, data={"value": 1}, ok=True,
        messages=({"role": "assistant", "content": "one"},), tool_events=(event,), raw_responses=({"source": "fixture"},),
        usage={"tool_calls": 1, "inference_requests": 0}, engine="python-runtime", model="fixture", mode="fixture",
        trace_schema_version="agentic_systems.trace.v1", validation={"ok": True, "issues": []}, errors=(),
        meta={"name": "parent"}, execution_id="parent", parent_execution_id=None, children=(child,))
    assert_result(result)
    assert result.model == "fixture" and result.tool_events[0].duration_ms == 0.1
    assert not replace(result, children=(replace(child, parent_execution_id="wrong"),)).check_invariants().ok
    assert not replace(result, usage={"tool_calls": -1}).check_invariants().ok
    with pytest.raises(TypeError):
        a.RunResult(data={"bad": math.inf})


def test_allow_policy_does_not_erase_recorded_partial_failure(monkeypatch):
    import agentic_systems._grammar as grammar
    monkeypatch.setattr(grammar, "_invoke_actor", lambda *args: a.RunResult(data={"value": 7}, ok=True,
        errors=({"code": "explicitly_allowed_partial_failure"},), engine="openai-runtime"))
    actor = a.Agent("model", runtime=a.runtime(provider="openai-runtime", model="fixture"), contract={"failure_policy": "allow"})
    result = actor.run({})
    assert result.ok and result.errors
    assert_result(result)
