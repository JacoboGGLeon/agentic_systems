"""Dev6 contracts: static checks, one context, root deadlines, graph composition."""

import asyncio
import inspect
import time
from dataclasses import replace
import pydantic
import pytest
import agentic_systems as t


class State(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    value: int
    label: str | None = None


def graph(fn):
    g = t.Graph(State)
    g.add_node("work", fn)
    g.add_edge(t.START, "work")
    g.add_edge("work", t.END)
    return g


@t.tool
def increment(value: int) -> dict:
    return {"value": value + 1}


def test_compile_checks_units_without_executing_work():
    effects = []

    @t.tool
    def operation(value: int) -> dict:
        effects.append(value)
        return {"value": value + 1}

    skill = t.skill(name="math", tools=(operation,))
    agent = t.Agent(
        "worker", runtime=t.runtime(provider="python-runtime"), skills=(skill,)
    )
    system = t.System(
        "app", graph(lambda state: agent.run({"value": state.value})), memory=t.Memory()
    )

    def records():
        effects.append("records")
        yield {"value": 1}

    env = t.Environment("env", graph(system), records=records)
    evaluation = t.Eval(
        "eval", system, ({"input": {"value": 1}, "expected": {"ok": True}},)
    )
    for unit in (agent, system, env, evaluation):
        unit.compile()
    assert effects == [] and system.memory.read() == []
    assert system.run({"value": 1}).data["value"] == 2
    assert effects == [1]


@pytest.mark.parametrize(
    "name",
    [
        "Limits",
        "Action",
        "Runtime",
        "Scheduler",
        "Policy",
        "Harness",
        "check",
        "StateGraph",
    ],
)
def test_removed_and_unnecessary_constructors_do_not_exist(name):
    assert not hasattr(t, name)


@pytest.mark.parametrize(
    "unit",
    [
        t.Agent("a", graph(increment)),
        t.System("s", graph(increment)),
        t.Environment("e", graph(increment), records=({"value": 1},)),
        t.Eval(
            "v",
            t.System("s", graph(increment)),
            cases=({"input": {"value": 1}, "expected": {"ok": True}},),
        ),
    ],
)
def test_one_run_signature_and_no_legacy_keyword(unit):
    assert "limits" not in inspect.signature(unit.run).parameters
    assert "timeout_s" in inspect.signature(unit.run).parameters
    assert "limits" not in inspect.signature(unit.compile().run).parameters
    with pytest.raises(TypeError):
        unit.run(limits={})
    with pytest.raises(TypeError):
        t.runtime(provider="python-runtime", max_actions=10)


@pytest.mark.parametrize("invalid", [0, -1, True, "2", float("inf"), float("nan")])
def test_bad_root_deadlines_rejected_before_effects(invalid):
    effects = []
    app = t.System("root", graph(lambda s: effects.append(1) or {"value": 2}))
    with pytest.raises(pydantic.ValidationError):
        app.run({"value": 1}, timeout_s=invalid)
    assert not effects


def test_more_nesting_and_many_nodes_do_not_change_acceptance():
    unit = t.Agent("leaf", graph(increment))
    for i in range(12):
        unit = t.System("nested" + str(i), graph(unit))
    output = unit.run({"value": 1})
    assert output.ok and output.data["value"] == 2
    g = t.Graph(State)
    last = t.START
    for i in range(260):
        name = "step" + str(i)
        g.add_node(name, lambda s: {"value": s.value + 1})
        g.add_edge(last, name)
        last = name
    g.add_edge(last, t.END)
    output = t.System("wide", g).run({"value": 0}, timeout_s=20)
    assert output.ok and output.data["value"] == 260, output.to_dict()
    assert output.meta["nodes_observed"] == 260


def test_root_deadline_shared_and_no_child_reset():
    effects = []

    def slow(s):
        time.sleep(0.025)
        effects.append(s.value)
        return {"value": s.value + 1}

    inner = t.System("inner", graph(slow))
    g = t.Graph(State)
    g.add_node("one", inner)
    g.add_node("two", inner)
    g.add_node("three", inner)
    g.add_edge(t.START, "one")
    g.add_edge("one", "two")
    g.add_edge("two", "three")
    g.add_edge("three", t.END)
    result = t.System("root", g).run({"value": 0}, timeout_s=0.04)
    assert not result.ok and len(effects) <= 2
    assert "deadline" in str(result.errors).lower()
    assert result.check_invariants().ok
    forbidden = t.System("bad", graph(lambda s: inner.run(s, timeout_s=1))).run(
        {"value": 0}
    )
    assert not forbidden.ok and "inherit" in str(forbidden.errors)


@pytest.mark.parametrize("async_node", [False, True])
def test_context_direct_and_async_node(async_node):
    observed = []

    def node(s, *, context: t.Context):
        observed.append(context.sources)
        return {"value": s.value + context.data["delta"]}

    async def anode(s, *, context: t.Context):
        return node(s, context=context)

    app = t.System(
        "context",
        graph(anode if async_node else node),
        context=t.Context({"delta": 3}, sources=("policy",)),
    )
    result = asyncio.run(app.arun({"value": 2}))
    assert result.ok and result.data["value"] == 5
    assert observed == [("policy",)]


@pytest.mark.parametrize(
    "node",
    [
        lambda s, context: {"value": 1},
        lambda s, *, context: {"value": 1},
        lambda s, runtime: {"value": 1},
    ],
)
def test_wrong_context_signatures_fail_at_compile(node):
    with pytest.raises(TypeError):
        t.System("bad", graph(node)).compile()


def test_context_tools_memory_and_lineage_survive_parallel_branches():
    seen = {}
    memory = t.Memory()
    memory.remember(t.RunResult(data={"value": 7}))

    class Branch(pydantic.BaseModel):
        value: int
        left: int | None = None
        right: int | None = None

    @t.tool
    def read(value: int, *, context: t.Context) -> dict:
        return {"value": value + context.data["delta"]}

    worker = t.Agent(
        "worker",
        runtime=t.runtime(provider="python-runtime"),
        skills=(t.skill(name="math", tools=(read,)),),
    )

    def left(s, *, context: t.Context):
        seen["left"] = context.to_dict()
        result = worker.run({"value": s.value})
        assert result.ok
        return {"left": result.data["value"]}

    def right(s, *, context: t.Context):
        seen["right"] = context.to_dict()
        return {"right": s.value + context.data["delta"]}

    g = t.Graph(Branch)
    g.add_node("before", lambda s: {"value": s.value + 1})
    g.add_node("left", left)
    g.add_node("right", right)
    g.add_edge(t.START, "before")
    g.add_edge("before", "left")
    g.add_edge("before", "right")
    g.add_edge("left", t.END)
    g.add_edge("right", t.END)
    result = t.System(
        "parallel",
        g,
        context=t.Context({"delta": 3}, sources=("policy",)),
        memory=memory,
    ).run({"value": 1})
    assert result.ok and result.data["left"] == result.data["right"] == 5, (
        result.to_dict()
    )
    assert seen["left"] == seen["right"]
    assert len(seen["left"]["episodes"]) == 1 and seen["left"]["sources"] == ["policy"]
    assert seen["left"]["lineage"]
    assert len(memory.read()) == 2


class Nullable(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    amount: int | None


def test_required_nullable_is_not_filled_or_coerced():
    effects = []
    g = t.Graph(Nullable)
    g.add_node("read", lambda s: effects.append(s.amount) or {"amount": s.amount})
    g.add_edge(t.START, "read")
    g.add_edge("read", t.END)
    app = t.System("nullable", g)
    assert app.run({"amount": None}).ok and effects == [None]
    for payload in ({}, {"amount": "null"}, {"amount": True}):
        assert not app.run(payload).ok
    assert effects == [None]


def test_pause_resume_preserves_work_and_does_not_charge_wait_time():
    effects = []

    def before(s):
        effects.append(1)
        return {"value": s.value + 1}

    def approval(s, *, context: t.Context):
        answer = t.pause({"question": "approve", "source": context.sources[0]})
        return {"value": s.value + int(answer)}

    g = t.Graph(State)
    g.add_node("before", before)
    g.add_node("approval", approval)
    g.add_edge(t.START, "before")
    g.add_edge("before", "approval")
    g.add_edge("approval", t.END)
    app = t.System("pause", g, context=t.Context({}, sources=("policy",))).compile()
    waiting = app.run({"value": 1}, timeout_s=1)
    assert waiting.status == "paused" and effects == [1]
    time.sleep(0.01)
    result = app.resume(waiting, True)
    assert result.ok and result.data["value"] == 3 and effects == [1]
    assert result.check_invariants().ok
    evaluation = t.Eval(
        "no_pause",
        t.System("target", g, context=t.Context({}, sources=("policy",))),
        cases=({"input": {"value": 1}, "expected": {"ok": False}},),
    )
    checked = evaluation.run()
    assert checked.ok and checked.status == "completed", checked.to_dict()


def test_projected_node_keeps_all_nested_runresults_and_failed_evidence():
    worker = t.Agent(
        "worker",
        runtime=t.runtime(provider="python-runtime"),
        skills=(t.skill(name="math", tools=(increment,)),),
    )

    def aggregate(s):
        first = worker.run({"value": s.value})
        second = worker.run({"value": s.value + 10})
        return {"value": first.data["value"] + second.data["value"]}

    output = t.System("aggregate", graph(aggregate)).run({"value": 1})
    assert output.ok and output.data["value"] == 14, output.to_dict()
    events = [e for n in output.walk() for e in n.tool_events]
    assert len(events) == 2 and sorted(e.input["value"] for e in events) == [1, 11]
    assert output.check_invariants().ok

    def discarded_failure(s):
        worker.run({"value": "invalid"})
        return {"value": 99}

    failed = t.System("failed", graph(discarded_failure)).run({"value": 1})
    assert not failed.ok and failed.errors
    assert failed.check_invariants().ok


def test_scheduler_does_not_reset_root_deadline_between_retries():
    from agentic_systems._engine.core.scheduler import (
        SchedulerConfig,
        execute_sync,
        _EXECUTION_DEADLINE,
        SchedulerTimeoutError,
    )

    attempts = []

    def failed():
        attempts.append(1)
        raise ConnectionError("fixture")

    token = _EXECUTION_DEADLINE.set(time.monotonic() + 0.03)
    try:
        with pytest.raises(SchedulerTimeoutError) as caught:
            execute_sync(
                failed, SchedulerConfig(max_retries=20, backoff_s=0.05, timeout_s=10)
            )
        assert len(attempts) == 1
        assert caught.value._agentic_scheduler_attempts == 1
    finally:
        _EXECUTION_DEADLINE.reset(token)
    value, meta = execute_sync(lambda: 7, SchedulerConfig())
    assert value == 7 and meta["attempts"] == 1


def test_returned_composition_does_not_duplicate_observed_calls():
    worker = t.Agent(
        "worker",
        runtime=t.runtime(provider="python-runtime"),
        skills=(t.skill(name="math", tools=(increment,)),),
    )

    def compose(state):
        raw = worker.run({"value": state.value})
        envelope = t.System("envelope", graph(lambda inner: raw))
        return replace(
            envelope.run({"value": state.value}), data={"value": raw.data["value"]}
        )

    result = t.System("root", graph(compose)).run({"value": 1})
    assert result.ok and result.data["value"] == 2, result.to_dict()
    assert result.check_invariants().ok
    assert len([e for n in result.walk() for e in n.tool_events]) == 1


def test_actor_retry_preserves_all_attempts_errors_usage_and_lineage(monkeypatch):
    from agentic_systems._engine.integrations.adapters.native import (
        NativeFrameworkAdapter,
    )
    from agentic_systems._engine.results import RunResult

    seen = []

    def run(self, agent, engine, input_value, policy, *, mode):
        seen.append(1)
        if len(seen) == 1:
            return RunResult(
                ok=False,
                data={"error": {"retryable": True}},
                errors=[{"code": "fixture_transient", "retryable": True}],
                usage={"requests": 1, "input_tokens": 2},
            )
        return RunResult(data={"value": 2}, usage={"requests": 1, "input_tokens": 3})

    monkeypatch.setattr(NativeFrameworkAdapter, "run", run)
    agent = t.Agent(
        "retry",
        runtime=t.runtime(provider="python-runtime", max_retries=1),
        skills=(t.skill(name="math", tools=(increment,)),),
    )
    result = agent.run({"value": 1})
    assert result.ok and len(seen) == 2, result.to_dict()
    histories = [
        n.meta["scheduler_execution"]["attempt_history"]
        for n in result.walk()
        if "scheduler_execution" in n.meta
    ]
    assert len(histories) == 1 and [r["status"] for r in histories[0]] == [
        "failed",
        "completed",
    ]
    assert histories[0][0]["result"]["errors"][0]["code"] == "fixture_transient"
    assert result.usage["requests"] == 2 and result.usage["input_tokens"] == 5
    attempts = [step for step in result.lineage().steps if step["kind"] == "attempt"]
    assert len(attempts) == 2 and attempts[0]["evidence"]["ok"] is False
    assert result.check_invariants().ok
