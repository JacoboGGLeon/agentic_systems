from dataclasses import replace

import pytest
import agentic_systems as a
from test_grammar import unit, assert_result


@a.tool
def echo(value: int) -> dict:
    return {"value": value}


def model(contract=None, **kwargs):
    return a.Agent("fixture", runtime=a.runtime(provider="python-runtime", max_tool_calls=1),
                   skills=(a.skill(name="echo", tools=[echo]),), contract=contract, **kwargs)


@pytest.mark.parametrize("expectation", [{"all_of": 1}, {"all_of": ["missing"]},
    {"all_of": ["echo"], "forbidden": ["echo"]}, {"all_of": ["echo"], "allowed": []},
    {"any_of": ["echo"], "forbidden": ["echo"]}, {"min_count": -1}, {"min_count": 2}])
def test_impossible_tool_contracts_fail_before_execution(expectation):
    with pytest.raises((TypeError, ValueError)):
        model({"tool_expectation": expectation}).compile()


@pytest.mark.parametrize("contract", [{"expected_output": []}, {"expected_tool_outputs": {"missing": {}}}, {"output_schema": []}])
def test_contract_payload_types_and_unknown_tool_expectations(contract):
    with pytest.raises((TypeError, ValueError)):
        model(contract).compile()


def test_required_tool_budget_and_policy_contradictions():
    worker = model({"tool_expectation": {"all_of": ["echo"]}})
    with pytest.raises(ValueError):
        replace(worker, runtime=a.runtime(provider="python-runtime", max_tool_calls=0)).compile()
    with pytest.raises(ValueError):
        replace(worker, policy={"tool_choice": "none"}).compile()
    with pytest.raises(ValueError):
        model({"completion": "always_finalize"}, policy={"finalize": "never"}).compile()
    positive = model({"tool_expectation": {"all_of": ["echo"], "allowed": ["echo"], "min_count": 1}}).run({"tool": "echo", "input": {"value": 3}})
    assert positive.ok, positive.to_dict()
    forbidden = model({"tool_expectation": {"forbidden": ["echo"]}}).run({"tool": "echo", "input": {"value": 3}})
    assert not forbidden.ok and any(e.name == "echo" for n in forbidden.walk() for e in n.tool_events)
    assert_result(forbidden)


@pytest.mark.parametrize("text", ["invalid JSON", "[]"])
def test_model_structured_text_errors_are_preserved(monkeypatch, text):
    import agentic_systems._grammar as implementation
    monkeypatch.setattr(implementation, "_invoke_actor", lambda *args: a.RunResult(text=text))
    result = model({"output_schema": {"type": "object"}}).run({})
    assert not result.ok and any(n.text == text for n in result.walk())
    assert_result(result)


@pytest.mark.parametrize("values", [{"model": ""}, {"endpoint": 1}, {"api_key": 1}])
def test_invalid_connection_value_types(values):
    with pytest.raises(TypeError):
        a.runtime(provider="openai-runtime", **values)


def test_artifact_profiles_and_native_options_are_explicit():
    with pytest.raises(ValueError):
        a.model_artifact("")
    with pytest.raises(ValueError):
        a.model_server(a.model_artifact("fixture"), profile="FAST")
    options = a.framework("openai-agents", agent_kwargs={"model_settings": {"parallel_tool_calls": True}})
    assert options.inspect()["agent_kwargs"] == {"model_settings": "dict"}


@pytest.mark.parametrize("payload", [{1: "bad-key"}, {"value": object()}, {"value": float('nan')}])
def test_invalid_business_json_is_a_serializable_failed_run(payload):
    result = unit().run(payload)
    assert not result.ok and result.meta["input_error"]
    assert_result(result)


@pytest.mark.parametrize("topology", [a.Sequence(()), a.Sequence([]), a.Sequence((a.Action("same", lambda d: d), a.Action("same", lambda d: d))),
    a.Graph([], (), "missing"), a.Graph((("a", a.Action("a", lambda d: d)), ("a", a.Action("b", lambda d: d))), (("a", "END"),), "a"),
    a.Graph((("a", a.Action("a", lambda d: d)),), (), "a"),
    a.Graph((("a", a.Action("a", lambda d: d)),), (("a", "END"),), "a", max_visits=0),
    a.Graph((("a", a.Action("a", lambda d: d)),), (("a", 1),), "a"),
    a.Parallel((a.Action("a", lambda d: d),), join=None), a.Action("bad", object()), a.Action("bad", lambda d: d, input=None), object()])
def test_malformed_flow_definitions_fail_at_compile(topology):
    with pytest.raises((TypeError, ValueError)):
        a.Agent("bad", topology).compile()


def test_owner_modes_bad_capabilities_and_recursive_definition():
    for options in ({"backend": "missing"}, {"skills": []}, {"skills": (object(),)}):
        with pytest.raises((TypeError, ValueError)):
            a.Agent("bad", a.Action("step", lambda d: d), **options).compile()
    with pytest.raises(ValueError):
        a.System("bad").compile()
    with pytest.raises(ValueError):
        a.Agent("", a.Action("a", lambda d: d)).compile()
    with pytest.raises(ValueError):
        a.Agent("bad")
    with pytest.raises(ValueError):
        a.Agent("bad", runtime=a.runtime(provider="python-runtime"), backend="unknown").compile()
    with pytest.raises(ValueError):
        a.Agent("bad", a.Action("a", lambda d: d), contract={"completion": "always_finalize"}).compile()
    for options in ({"runtime": {}}, {"runtime": a.runtime(provider="python-runtime"), "instructions": 1},
                    {"runtime": a.runtime(provider="python-runtime"), "framework": "native"},
                    {"runtime": a.runtime(provider="openai-runtime")}):
        with pytest.raises((TypeError, ValueError)):
            a.Agent("bad", **options).compile()
    with pytest.raises(TypeError):
        unit().run({}, limits={})
    cyclic = a.Agent("cyclic", a.Action("a", lambda d: d))
    object.__setattr__(cyclic, "flow", cyclic)
    with pytest.raises(ValueError):
        cyclic.compile()


def test_late_join_model_episode_and_eval_keep_evidence(monkeypatch):
    import agentic_systems._grammar as implementation
    clock = [0.0]
    monkeypatch.setattr(implementation.time, "monotonic", lambda: clock[0])
    def late_join(rows):
        clock[0] = 2.0
        return rows["a"]
    parallel = a.Agent("parallel", a.Parallel((a.Action("a", lambda d: d),), join=late_join)).run({"value": 1}, limits=a.Limits(timeout_s=1))
    assert not parallel.ok and any(n.data == {"value": 1} for n in parallel.walk())
    clock[0] = 0.0
    def late_actor(*args):
        clock[0] = 2.0
        return a.RunResult(data={"value": 7})
    monkeypatch.setattr(implementation, "_invoke_actor", late_actor)
    late = model().run({}, limits=a.Limits(timeout_s=1))
    assert not late.ok and late.data == {"value": 7}
    clock[0] = 0.0
    def late_stop(memory, result):
        clock[0] = 2.0
        return True
    episode = a.Environment("late", unit(), ({"value": 1},), stop=late_stop).run(limits=a.Limits(timeout_s=1))
    assert not episode.ok and len(episode.data["history"]) == 1 and episode.children[0].ok
    clock[0] = 0.0
    # Exhaustion after a completed check must not duplicate a case row.
    def slow_check(result, case):
        clock[0] = 2.0
        return {"ok": True, "issues": []}
    evaluated = a.Eval("late", unit(), ({"input": {"value": 1}, "expected": {"ok": True}},), checks=(slow_check,)).run(limits=a.Limits(timeout_s=1))
    assert not evaluated.ok and len(evaluated.data["cases"]) == 1


@pytest.mark.parametrize("verdict", [{"criteria": {}}, {"criteria": {"correctness": 2}},
    {"criteria": {"correctness": 1}, "findings": {}}, {"criteria": {"correctness": 1}, "findings": [{"criterion": "missing", "evidence": "bad"}]}])
def test_invalid_judge_payloads_block_acceptance(verdict):
    judge = a.Agent("fixture", a.Action("judge", lambda d: verdict))
    result = a.Eval("invalid", unit(), ({"input": {"value": 1}},), judge=judge, rubric={"criteria": ["correctness"]}).run()
    assert not result.ok and len(result.children) == 2
    assert_result(result)


def test_invalid_expected_metrics_stop_and_mutated_result_are_detected():
    with pytest.raises(TypeError):
        a.Eval("bad", unit(), ({"input": {}, "expected": {"data": []}},)).compile()
    wrong_metrics = a.Eval("bad", unit(), ({"input": {"value": 1}},), checks=(lambda result, case: {"ok": True, "issues": [], "metrics": []},)).run()
    assert not wrong_metrics.ok
    episode = a.Environment("bad", unit(), ({"value": 1},), stop=lambda memory, result: "yes").run()
    assert not episode.ok
    imported = a.RunResult(data={"value": 1}, children=(a.RunResult(data={"value": 1}, ok=False, errors=({"code": "controlled"},)),))
    guarded = a.Agent("guarded", a.Action("imported", lambda data: imported)).run({})
    assert not guarded.ok and any(e["code"] == "invariant_failed" for e in guarded.errors)


def test_result_import_validation_and_lineage_retains_routes_and_limits_rows():
    for values in ({"data": {1: "bad"}}, {"ok": 1}, {"children": (1,)}, {"tool_events": (1,)}):
        with pytest.raises(TypeError):
            a.RunResult(**values)
    child = a.RunResult(data={}, execution_id="same", parent_execution_id="parent")
    invalid = a.RunResult(execution_id="parent", children=(child, child))
    assert not invalid.check_invariants().to_dict()["ok"]
    duplicate = a.RunResult(tool_events=({"id": "same", "name": "a"}, {"id": "same", "name": "b"}))
    assert not duplicate.check_invariants().ok
    @a.tool
    def rows() -> dict:
        return {"rows": [1, 2, 3]}
    flow = a.Graph((("rows", a.Action("rows", rows)),), (("rows", lambda data: "END"),), "rows")
    result = a.Agent("rows", flow).run({})
    lineage = result.lineage(max_tool_rows=1)
    assert any(s["kind"] == "decision" for s in lineage.steps)
    assert [s["evidence"]["output"]["data"]["rows"] for s in lineage.steps if s["kind"] == "tool"] == [[1]]
    assert set(s["kind"] for s in lineage.steps) <= {"execution", "decision", "tool"}
    with pytest.raises(ValueError):
        result.lineage(max_tool_rows=-1)
    with pytest.raises(ValueError):
        lineage.to_prompt_context(max_chars=0)


def test_private_actor_conversion_preserves_delegated_children(monkeypatch):
    import agentic_systems._engine.factories as implementation
    from agentic_systems._engine.results import RunResult
    class Actor:
        def run(self, input):
            return RunResult(data={"value": 1}, children=[RunResult(data={"value": 1})])
    monkeypatch.setattr(implementation, "agent", lambda **kwargs: Actor())
    result = model().run({})
    assert result.ok and len(list(result.walk())) >= 4
    assert_result(result)


def test_invalid_tools_and_skill_loading(tmp_path):
    async def asynchronous():
        return {}
    with pytest.raises(TypeError):
        a.tool(asynchronous)
    with pytest.raises(ValueError):
        a.tool(lambda: {}, name="")
    for options in ({"name": ""}, {"name": "bad", "tools": [object()]}, {"name": "bad", "instructions": 1}):
        with pytest.raises((TypeError, ValueError)):
            a.skill(**options)
    with pytest.raises(ValueError):
        a.load_skill(tmp_path)
    (tmp_path / "__init__.py").write_text("MARKER=True\n", encoding="utf-8")
    (tmp_path / "SKILL.md").write_text("# Invalid", encoding="utf-8")
    (tmp_path / "skill.py").write_text("def build_skill(): return None\n", encoding="utf-8")
    with pytest.raises(TypeError):
        a.load_skill(tmp_path)
