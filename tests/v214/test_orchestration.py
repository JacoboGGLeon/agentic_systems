"""Common graph, actor separation and process-local continuation contracts."""
import asyncio
import json
import time

import pytest
import agentic_systems as toolkit


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("flow", ["sequence", "parallel", "graph"])
def test_one_graph_ir(backend, flow):
    a = toolkit.Action("a", lambda d: {"value": d["value"] + 1})
    b = toolkit.Action("b", lambda d: {"value": d["value"] * 2})
    if flow == "sequence":
        plan, expected = toolkit.Sequence((a, b)), 6
    elif flow == "parallel":
        plan, expected = toolkit.Parallel((a, b), join=lambda rows: {"value": sum(r["value"] for r in rows.values())}), 7
    else:
        plan, expected = toolkit.Graph((("a", a), ("b", b)), (("a", lambda d: "b"), ("b", "END")), "a"), 6
    program = toolkit.Agent("operator", plan, backend=backend).compile()
    assert program.inspect()["children"][0]["graph"]["schema"] == "agentic_systems.graph.v1"
    output = program.run({"value": 2})
    assert output.ok and output.data == {"value": expected}, output.to_dict()


def test_langgraph_is_not_an_actor_framework():
    with pytest.raises(ValueError, match="orchestration backend"):
        toolkit.framework("langgraph")


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_python_actors_on_both_graph_engines(backend, framework):
    @toolkit.tool
    def double(value: int) -> dict:
        return {"value": value * 2}
    actor = toolkit.Agent("operator", runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(framework), skills=(toolkit.skill(name="arithmetic", tools=[double]),))
    system = toolkit.System("test", toolkit.Sequence((actor,)), backend=backend)
    output = system.run({"tool": "double", "input": {"value": 3}})
    assert output.ok and output.data == {"value": 6}, output.to_dict()
    assert output.usage.get("inference_requests", 0) == 0


def approval(value):
    return {**value, "approved": toolkit.pause({"question": "Approve?", "value": value})}


def test_pause_resume_preserves_completed_operations_and_budget():
    calls = []
    def before(d):
        calls.append(d)
        return {"value": d["value"] + 1}
    system = toolkit.System("approval", toolkit.Sequence((
        toolkit.Agent("work", toolkit.Sequence((toolkit.Action("before", before),))),
        toolkit.Agent("decision", toolkit.Action("approve", approval)),
        toolkit.Action("after", lambda d: {**d, "done": True}),
    )), backend="langgraph").compile()
    waiting = system.run({"value": 1}, limits=toolkit.Limits(max_actions=3))
    assert waiting.status == "paused" and waiting.ok and not waiting.errors, waiting.to_dict()
    assert waiting.check_invariants().ok and len(calls) == 1
    assert waiting.meta["actions_observed"] == 2
    serialized = toolkit.RunResult(**json.loads(json.dumps(waiting.to_dict())))
    output = system.resume(serialized, True)
    assert output.ok and output.status == "completed" and output.data == {"value": 2, "approved": True, "done": True}, output.to_dict()
    assert len(calls) == 1 and output.meta["actions_observed"] == 3
    assert output.check_invariants().ok
    with pytest.raises(ValueError, match="stale or completed"):
        system.resume(waiting, True)


def test_multiple_pauses_are_one_shot_and_owned():
    definition = toolkit.Agent("approvals", toolkit.Sequence((toolkit.Action("first", approval), toolkit.Action("second", approval))), backend="langgraph")
    program, other = definition.compile(), definition.compile()
    first = program.run({"value": 2})
    with pytest.raises(ValueError, match="another compiled"):
        other.resume(first, True)
    second = program.resume(first, True)
    assert second.status == "paused"
    with pytest.raises(ValueError, match="stale"):
        program.resume(first, True)
    final = asyncio.run(program.aresume(second, False))
    assert final.ok and final.data["approved"] is False


def test_human_wait_is_excluded_from_active_deadline():
    program = toolkit.Agent("approval", toolkit.Action("pause", approval), backend="langgraph").compile()
    waiting = program.run({}, limits=toolkit.Limits(timeout_s=1))
    assert waiting.status == "paused"
    time.sleep(1.05)
    assert program.resume(waiting, True).ok


def test_pause_rejected_on_native_and_eval():
    native = toolkit.Agent("approval", toolkit.Action("pause", approval))
    output = native.run({})
    assert not output.ok and "backend='langgraph'" in str(output.errors)
    evaluation = toolkit.Eval("no-continuation", toolkit.Agent("a", toolkit.Action("pause", approval), backend="langgraph"),
        ({"input": {}, "expected": {"ok": True}},)).run()
    assert not evaluation.ok and "outside actors and Eval" in str(evaluation.errors)


def test_environment_uses_graph_and_does_not_repeat_records_on_resume():
    seen, closed, calls = [], [], []
    def source():
        try:
            for i in range(2):
                seen.append(i)
                yield {"value": i}
        finally:
            closed.append(True)
    def work(d):
        calls.append(d["value"])
        return d
    unit = toolkit.System("work", toolkit.Sequence((toolkit.Action("work", work), toolkit.Action("approve", approval))))
    program = toolkit.Environment("episode", unit, source, backend="langgraph").compile()
    assert program.inspect()["graph"]["schema"] == "agentic_systems.graph.v1"
    first = program.run()
    assert first.status == "paused" and seen == [0] and calls == [0] and not closed, first.to_dict()
    second = program.resume(first, True)
    assert second.status == "paused" and seen == [0, 1] and calls == [0, 1], second.to_dict()
    final = program.resume(second, False)
    assert final.ok and final.data["summary"]["processed"] == 2, final.to_dict()
    assert calls == [0, 1] and closed == [True]
    assert final.check_invariants().ok


def test_child_backend_conflict_is_explicit():
    with pytest.raises(ValueError, match="backend"):
        toolkit.System("conflict", toolkit.Sequence((toolkit.Agent("child", toolkit.Action("a", lambda d: d), backend="native"),)), backend="langgraph").compile()


def test_parallel_pause_does_not_repeat_the_other_branch():
    calls = []
    def completed(d):
        calls.append(1)
        return {"value": 8}
    program = toolkit.System("fork", toolkit.Parallel((toolkit.Action("completed", completed), toolkit.Action("approval", approval)),
        join=lambda rows: {"value": rows["completed"]["value"], "approved": rows["approval"]["approved"]}), backend="langgraph").compile()
    waiting = program.run({})
    assert waiting.status == "paused" and len(calls) == 1
    finished = program.resume(waiting, True)
    assert finished.ok and finished.data == {"value": 8, "approved": True} and len(calls) == 1, finished.to_dict()


def test_context_and_memory_are_snapshotted_until_completion():
    memory = toolkit.Memory()
    @toolkit.tool
    def evidence(*, context: toolkit.Context) -> dict:
        return {"currency": context.data["currency"], "episodes": len(context.episodes)}
    program = toolkit.Agent("remember", toolkit.Sequence((toolkit.Action("approval", approval), toolkit.Action("evidence", evidence, input=lambda d: {}))),
        backend="langgraph", context=toolkit.Context({"currency": "MXN"}), memory=memory).compile()
    waiting = program.run({})
    assert waiting.status == "paused" and memory.read() == []
    assert "PAUSED" in waiting.lineage().render()
    assert json.loads(waiting.lineage().to_prompt_context())["status"] == "paused"
    memory.remember(toolkit.RunResult(data={"external": True}))
    final = program.resume(waiting, True)
    assert final.ok and final.data == {"currency": "MXN", "episodes": 0}, final.to_dict()
    assert len(memory.read()) == 2


def test_loop_visits_and_episode_steps_are_not_replay_cache_hits():
    calls = []
    def visit(d):
        calls.append(1)
        return {"value": len(calls)}
    plan = toolkit.Graph((("visit", toolkit.Action("visit", visit)),), (("visit", lambda d: "visit" if d["value"] < 3 else "END"),), "visit")
    output = toolkit.Agent("loop", plan, backend="langgraph").run({})
    assert output.ok and output.data == {"value": 3} and len(calls) == 3


def test_paused_usage_includes_completed_work_without_replay():
    program = toolkit.System("usage", toolkit.Sequence((
        toolkit.Action("metered", lambda d: toolkit.RunResult(data={}, usage={"inference_requests": 1, "input_tokens": 10})),
        toolkit.Action("approval", approval),
    )), backend="langgraph").compile()
    waiting = program.run({})
    assert waiting.status == "paused" and waiting.usage["inference_requests"] == 1
    final = program.resume(waiting, True)
    assert final.ok and final.usage["inference_requests"] == 1


def test_parallel_failure_overrides_pending_human_approval():
    def fail(d):
        raise ValueError("mandatory branch failed")
    program = toolkit.System("failure", toolkit.Parallel((toolkit.Action("fail", fail), toolkit.Action("approval", approval)),
        join=lambda d: d), backend="langgraph").compile()
    output = program.run({})
    assert output.status == "failed" and not output.ok and output.continuation is None, output.to_dict()
    assert "mandatory branch failed" in str(output.errors) and output.check_invariants().ok
