import asyncio
from dataclasses import replace
import importlib
import json

import pytest
import agentic_systems as a


def increment(data):
    return {"value": data["value"] + 1}


def double(data):
    return {"value": data["value"] * 2}


def unit(backend="native"):
    return a.Agent("worker", a.Sequence((a.Action("inc", increment), a.Action("double", double))), backend=backend)


def assert_result(result):
    assert result.check_invariants().ok, result.check_invariants().to_dict()
    assert a.RunResult(**json.loads(json.dumps(result.to_dict()))).to_dict() == result.to_dict()


@pytest.mark.parametrize("owner", [a.Agent, a.System])
@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("flow", ["sequence", "parallel", "graph"])
def test_six_flows_direct_compiled_sync_async(owner, backend, flow):
    first, second = a.Action("inc", increment), a.Action("double", double)
    if owner is a.System:
        first, second = a.Agent("inc_agent", first), a.Agent("double_agent", second)
    if flow == "sequence":
        topology, expected = a.Sequence((first, second)), 8
    elif flow == "parallel":
        topology, expected = a.Parallel((first, second), lambda rows: {"value": sum(r["value"] for r in rows.values())}), 10
    else:
        topology, expected = a.Graph((("inc", first), ("double", second)), (("inc", lambda d: "double" if d["value"] >= 0 else "END"), ("double", "END")), "inc"), 8
    target = owner("owner", topology, backend=backend)
    compiled = target.compile()
    for result in (target.run({"value": 3}), compiled.run({"value": 3}), asyncio.run(target.arun({"value": 3})), asyncio.run(compiled.arun({"value": 3}))):
        assert result.ok and result.data == {"value": expected}, result.to_dict()
        assert_result(result)
    assert compiled.inspect() == target.inspect()
    if flow == "graph":
        assert target.run({"value": -3}).data == {"value": -2}


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_graph_cycles_destinations_limits_and_failure_lineage(backend):
    step = a.Action("inc", increment)
    loop = a.Graph((("inc", step),), (("inc", lambda d: "inc" if d["value"] < 3 else "END"),), "inc", max_visits=4)
    result = a.Agent("loop", loop, backend=backend).run({"value": 0})
    assert result.ok and result.data["value"] == 3
    assert_result(result)
    for topology in (replace(loop, max_visits=1), replace(loop, edges=(("inc", lambda d: "missing"),))):
        failed = a.Agent("bad", topology, backend=backend).run({"value": 0})
        assert not failed.ok and any(n.data.get("value") == 1 for n in failed.walk())
        assert_result(failed)
    with pytest.raises(ValueError):
        a.Agent("bad", replace(loop, edges=(("inc", "missing"),)), backend=backend).compile()


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_parallel_isolates_inputs_retains_failure_and_skips_join(backend):
    joined = []
    def changed(d):
        d["items"].append(2)
        return d
    def broken(d):
        assert d["items"] == [1]
        raise RuntimeError("controlled")
    payload = {"items": [1]}
    target = a.System("branches", a.Parallel((a.Action("changed", changed), a.Action("broken", broken)), lambda rows: joined.append(True)), backend=backend)
    result = target.run(payload)
    assert not result.ok and not joined and payload == {"items": [1]}
    assert result.data["branches"]["changed"] == {"items": [1, 2]}
    assert_result(result)


def test_compilation_is_pure_capture_and_budgets_are_shared(monkeypatch):
    import agentic_systems._grammar as implementation
    calls = []
    def forbidden(*args):
        calls.append(True)
        raise AssertionError("must not execute")
    monkeypatch.setattr(implementation, "_invoke_actor", forbidden)
    a.Agent("model", runtime=a.runtime(provider="openai-runtime", model="explicit"), instructions="configured only").compile().inspect()
    a.Agent("callbacks", a.Graph((("step", a.Action("step", forbidden)),), (("step", forbidden),), "step")).inspect()
    episode = a.Environment("episode", unit(), ({"value": 1},), memory={}, observe=forbidden, update=forbidden, stop=forbidden)
    episode.compile().inspect()
    a.Eval("eval", unit(), ({"input": {"value": 1}, "expected": {"ok": True}},), checks=(forbidden,)).compile().inspect()
    assert not calls
    failed = unit().run({"value": 1}, limits=a.Limits(max_actions=1))
    assert not failed.ok and failed.meta["actions_observed"] == 1
    assert_result(failed)


def test_cooperative_timeout_retains_late_result(monkeypatch):
    import agentic_systems._grammar as implementation
    now = [0.0]
    monkeypatch.setattr(implementation.time, "monotonic", lambda: now[0])
    @a.tool
    def late(value: int) -> dict:
        now[0] = 2.0
        return {"value": value}
    result = a.Agent("late", a.Action("late", late)).run({"value": 7}, limits=a.Limits(timeout_s=1))
    assert not result.ok and any(r.data == {"value": 7} for r in result.walk())
    assert any(n.tool_events for n in result.walk())
    assert_result(result)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_real_episode_memory_stop_replay_and_eval_episode(backend):
    worker = a.Agent("sum", a.Action("sum", lambda d: {"total": d["previous"] + d["amount"]}), backend=backend)
    episode = a.Environment("ledger", worker, ({"amount": 2}, {"amount": 3}, {"amount": 100}), memory={"total": 0},
        observe=lambda row, memory: {"amount": row["amount"], "previous": memory["total"]},
        update=lambda memory, row, result: result.data,
        stop=lambda memory, result: memory["total"] >= 5)
    captured = episode.compile()
    for run in (episode.run(), captured.run(), asyncio.run(episode.arun()), asyncio.run(captured.arun())):
        assert run.ok and run.data["outputs"] == [{"total": 2}, {"total": 5}]
        assert run.data["summary"]["memory"] == {"total": 5}
        assert run.data["summary"]["terminated"] and not run.data["summary"]["truncated"]
        assert_result(run)
    assert captured.inspect() == episode.inspect()
    result = a.Eval("episode_contract", episode, ({"input": {"records": [{"amount": 4}], "memory": {"total": 10}}, "expected": {"ok": True}},),
        checks=(lambda result, case: {"ok": result.data["summary"]["memory"] == {"total": 14}, "issues": [], "metrics": {"reward": 14}},)).run()
    assert result.ok, result.to_dict()
    assert result.data["cases"][0]["checks"][1]["metrics"]["reward"] == 14
    assert_result(result)
    truncated = replace(episode, max_steps=1, stop=None).run()
    assert not truncated.ok and truncated.data["summary"]["truncated"]
    assert_result(truncated)


@pytest.mark.parametrize("stage", ["observe", "update", "stop"])
def test_episode_callback_failures_are_not_silent(stage):
    def broken(*args):
        raise ValueError("controlled " + stage)
    episode = a.Environment("bad", unit(), ({"value": 1},), **{stage: broken})
    result = episode.run()
    assert not result.ok and "controlled " + stage in str(result.errors)
    if stage != "observe":
        assert result.children and result.children[0].ok
    assert_result(result)


def test_eval_checks_negative_controls_expected_failures_and_async():
    good = a.Eval("ok", unit(), ({"input": {"value": 3}, "expected": {"ok": True, "data": {"value": 8}}},),
        checks=(lambda result, case: {"ok": result.data["value"] > 0, "issues": []},))
    for r in (good.run(), good.compile().run(), asyncio.run(good.arun()), asyncio.run(good.compile().arun())):
        assert r.ok and r.data["passed"] == 1
        assert_result(r)
    assert good.inspect() == good.compile().inspect()
    bad = replace(good, cases=({"input": {"value": 3}, "expected": {"data": {"value": 999}}},)).run()
    assert not bad.ok and bad.children[0].ok
    assert_result(bad)
    failing = a.Agent("fails", a.Action("fail", lambda d: (_ for _ in ()).throw(RuntimeError("controlled"))))
    expected = a.Eval("expected", failing, ({"input": {}, "expected": {"ok": False}},)).run()
    assert expected.ok and not expected.children[0].ok, expected.to_dict()
    assert_result(expected)


@pytest.mark.parametrize("score,claimed,findings,expected", [(1, True, [], True), (0.2, False, [{"criterion": "correctness", "evidence": "wrong fixture result"}], False),
    (0.2, True, [{"criterion": "correctness", "evidence": "wrong fixture result"}], False), (0.2, False, [], False)])
def test_explicit_judge_preserves_raw_verdict_and_never_overrides_checks(score, claimed, findings, expected):
    judge = a.Agent("fixture_judge", a.Action("judge", lambda payload: {"criteria": {"correctness": score}, "ok": claimed, "findings": findings}))
    target = a.Eval("judged", unit(), ({"input": {"value": 3}, "expected": {"data": {"value": 8}}},),
        judge=judge, rubric={"criteria": ["correctness"], "threshold": 0.8})
    result = target.run()
    assert result.ok == expected, result.to_dict()
    assert result.meta["judge_mode"] == "deterministic-fixture"
    assert len(result.children) == 2
    assert_result(result)
    if expected:
        negative = replace(target, checks=(lambda result, case: {"ok": False, "issues": [{"code": "controlled_negative"}]},)).run()
        assert not negative.ok and negative.data["cases"][0]["judge"]["ok"]


@pytest.mark.parametrize("case", [{"input": {}}, {"input": {}, "expected": {}}, {"input": {}, "expected": {"data_contains": {}}}, {"input": {}, "expected": {"ok": 1}}])
def test_vacuous_and_unknown_eval_contracts_rejected(case):
    with pytest.raises((TypeError, ValueError)):
        a.Eval("bad", unit(), (case,)).compile()


def test_removed_import_paths_and_public_methods():
    for module in ("agents", "system", "factories", "core", "providers", "integrations", "tools", "skills", "results", "contracts", "scaffolding", "compat"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("agentic_systems." + module)
    for name in ("agent", "system", "graph", "environment", "eval", "Route", "Tool", "Skill", "RuntimeConfig", "AgenticSystem"):
        assert not hasattr(a, name)
    for name in ("model_validate", "normalized", "native_result", "compact_trace", "validate", "apply_validation"):
        assert not hasattr(a.RunResult, name)
    with pytest.raises(TypeError):
        a.System("bad", a.Action("a", increment), skills=())
    with pytest.raises(TypeError):
        a.runtime(provider="python-runtime", model_id="alias")
    with pytest.raises(ValueError):
        a.framework("openai_agents")
    with pytest.raises(TypeError):
        a.tool(input_model=object)


@pytest.mark.parametrize("values", [{"max_actions": 0}, {"max_actions": True}, {"timeout_s": 0}, {"timeout_s": float('nan')}])
def test_invalid_limits(values):
    with pytest.raises(ValueError):
        a.Limits(**values)
