import asyncio
import json
import socket
import subprocess
import sys
import threading
import time
from dataclasses import replace

import agentic_systems as toolkit
import pytest

from unified_grammar import (
    Action,
    Agent,
    Environment,
    Eval,
    Graph,
    Limits,
    Parallel,
    Route,
    Sequence,
    System,
)
from unified_grammar.demo import (
    CAPABILITIES,
    EXPECTED,
    build,
    episode,
    evaluation,
    nested_application,
)


def assert_tree(root):
    nodes = list(root.walk())
    assert len({node.execution_id for node in nodes}) == len(nodes)
    for node in nodes:
        for child in node.children:
            assert child.parent_execution_id == node.execution_id
    encoded = json.loads(json.dumps(root.to_dict(), allow_nan=False))
    assert toolkit.RunResult.model_validate(encoded).ok == root.ok
    json.dumps(root.normalized(), allow_nan=False)
    root.lineage()


@pytest.mark.parametrize("owner", ["Agent", "System"])
@pytest.mark.parametrize("flow", list(EXPECTED))
@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_owner_flow_backend_direct_and_compiled(owner, flow, backend):
    unit = build(owner, flow, backend)
    prepared = unit.compile()
    payload = {"value": 3}
    direct = unit.run(payload)
    explicit = prepared.run(payload)
    assert direct.ok and explicit.ok
    assert direct.data == explicit.data == {"value": EXPECTED[flow]}
    assert payload == {"value": 3}
    assert direct.execution_id != explicit.execution_id
    assert direct.meta["prototype_kind"] == owner.lower()
    events = [event for node in direct.walk() for event in node.tool_events]
    assert len(events) == len({event.id for event in events}) == 2
    assert_tree(direct)
    assert_tree(explicit)
    if backend == "langgraph":
        body = prepared.prepared.children[0]
        assert type(body.native).__name__ == "CompiledStateGraph"
        assert len(body.native.get_graph().nodes) >= 4


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("legacy_route", [False, True])
def test_compile_and_inspect_do_not_call_any_user_stage(backend, legacy_route):
    calls = []

    def forbidden(*args):
        calls.append(args)
        raise AssertionError("compile executed an action/router/input/reducer")

    flow = Graph(
        nodes=(
            (
                "fork",
                Parallel(
                    (Action("a", forbidden, forbidden), Action("b", forbidden)),
                    forbidden,
                ),
            ),
        ),
        edges=(("fork", Route(forbidden, ("END",)) if legacy_route else forbidden),),
        start="fork",
    )
    unit = Agent("pure", flow, backend=backend)
    unit.compile()
    unit.compile()
    assert unit.inspect()["kind"] == "agent"
    assert calls == []


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_parallel_is_concurrent_isolated_and_joined_in_declared_order(backend):
    barrier = threading.Barrier(2, timeout=2)

    def left(value):
        value["items"].append("left")
        barrier.wait()
        return value

    def right(value):
        barrier.wait()
        return value

    order = []

    def join(values):
        order.extend(values)
        return {"left": values["left"]["items"], "right": values["right"]["items"]}

    payload = {"items": []}
    unit = Agent(
        "parallel",
        Parallel((Action("left", left), Action("right", right)), join),
        backend=backend,
    )
    output = unit.run(payload)
    assert output.ok
    assert output.data == {"left": ["left"], "right": []}
    assert payload == {"items": []}
    assert order == ["left", "right"]


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_graph_contains_fork_join_and_bounded_conditional_loop(backend):
    fork = Parallel(
        (
            Action("x", lambda d: {"value": d["value"] + 1}),
            Action("y", lambda d: {"value": d["value"] + 2}),
        ),
        lambda branches: {"value": sum(d["value"] for d in branches.values())},
    )
    loop = Graph(
        nodes=(("work", Action("inc", lambda d: {"value": d["value"] + 1})),),
        edges=(
            (
                "work",
                lambda d: "work" if d["value"] < 3 else "END",
            ),
        ),
        start="work",
        max_visits=4,
    )
    flow = Graph(
        nodes=(("loop", loop), ("fork", fork)),
        edges=(("loop", "fork"), ("fork", "END")),
        start="loop",
    )
    output = System("nested_graph", flow, backend=backend).run({"value": 0})
    assert output.ok and output.data == {"value": 9}
    assert_tree(output)
    failed = Agent("bound", replace(loop, max_visits=2), backend=backend).run(
        {"value": 0}
    )
    assert not failed.ok
    assert any("visit limit" in str(node.errors) for node in failed.walk())


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_errors_keep_completed_sibling_tool_and_skip_join(backend):
    observed = []

    @toolkit.tool
    def explode(value: int) -> dict:
        """Produce an intentional local failure."""
        raise ValueError("controlled-prototype-failure")

    @toolkit.tool
    def complete(value: int) -> dict:
        """Observe a successful sibling action."""
        observed.append(value)
        return {"value": value}

    joins = []
    output = Agent(
        "fail",
        Parallel(
            (Action("fail", explode), Action("success", complete)),
            lambda d: joins.append(d) or d,
        ),
        backend=backend,
    ).run({"value": 3})
    assert not output.ok and observed == [3] and joins == []
    events = [event for node in output.walk() for event in node.tool_events]
    assert {(event.name, event.ok) for event in events} == {
        ("explode", False),
        ("complete", True),
    }
    assert_tree(output)


def test_nested_owner_backend_identity_and_global_budget():
    outer = nested_application()
    output = outer.run({"value": 3})
    assert output.ok and output.data == {"value": 8, "approved": True}
    owners = [
        (n.meta["name"], n.meta["prototype_kind"], n.meta.get("backend"))
        for n in output.walk()
        if n.meta.get("prototype_kind") in {"agent", "system"}
    ]
    assert owners == [
        ("purchase_fixture", "system", "native"),
        ("agent_sequential", "agent", "langgraph"),
        ("decision", "agent", "native"),
    ]
    limited = outer.run({"value": 3}, limits=Limits(max_actions=2))
    assert not limited.ok and limited.meta["actions_observed"] == 2
    nested = System("parent", Sequence((outer,)))
    assert nested.run({"value": 3}).data == output.data
    assert_tree(nested.run({"value": 3}))


@pytest.mark.parametrize("framework", ["native", "langgraph"])
def test_real_python_runtime_agent_can_be_a_leaf_without_changing_framework(framework):
    raw = toolkit.agent(
        name="legacy_python",
        skills=[CAPABILITIES],
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=framework,
    )
    action = Action("legacy", raw, input=lambda d: {"tool": "increment", "input": d})
    output = Agent("owned", Sequence((action,)), backend="langgraph").run({"value": 3})
    assert output.ok and output.data["value"] == 4
    leaf = next(
        n for n in output.walk() if n.meta.get("name") != "legacy" and n.tool_events
    )
    assert leaf.engine == "python-runtime" and raw.framework_config.name == framework
    assert len([event for n in output.walk() for event in n.tool_events]) == 1
    assert not hasattr(raw, "compile")


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("flow", list(EXPECTED))
def test_environment_and_eval_use_real_212_contracts(flow, backend):
    unit = build("System", flow, backend)
    env = Environment("episode", unit, ({"value": 3}, {"value": 3}))
    compiled = env.compile()
    first, second = env.run(), compiled.run()
    assert first.ok and second.ok
    assert (
        first.data["outputs"]
        == second.data["outputs"]
        == [{"value": EXPECTED[flow]}] * 2
    )
    assert first.data["summary"]["memory"] == {"processed": 2}
    assert second.data["summary"]["memory"] == {"processed": 2}
    assert (
        first.data["history"][0]["episode_id"]
        != second.data["history"][0]["episode_id"]
    )
    cases = ({"input": {"value": 3}, "expected": {"data": {"value": EXPECTED[flow]}}},)
    good = Eval("measure", unit, cases)
    assert good.run().ok and good.compile().run().ok
    bad = Eval(
        "negative_control",
        unit,
        ({"input": {"value": 3}, "expected": {"data": {"value": -999}}},),
    ).run()
    assert not bad.ok and bad.data["failed"] == 1
    assert_tree(first)


def test_episode_truncation_and_eval_shared_action_limit():
    env = replace(episode(), max_steps=1).run()
    assert not env.ok and len(env.data["outputs"]) == 1
    judged = evaluation().run(limits=Limits(max_actions=2))
    assert not judged.ok and judged.meta["actions_observed"] == 2


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_late_tool_completion_is_preserved_as_a_timeout(backend):
    @toolkit.tool
    def late(value: int) -> dict:
        """Finish after the cooperative run deadline."""
        time.sleep(0.15)
        return {"value": value}

    output = Agent(
        "deadline",
        Parallel((Action("late", late),), lambda d: d["late"]),
        backend=backend,
    ).run({"value": 3}, limits=Limits(timeout_s=0.1))
    assert not output.ok
    assert any(event.ok for n in output.walk() for event in n.tool_events)
    assert any("TimeoutError" in str(n.errors) for n in output.walk())


def test_legacy_212_paths_and_exports_are_unchanged():
    assert toolkit.__version__ == "2.1.2" and len(toolkit.__all__) == 89
    raw = toolkit.agent(
        name="original",
        skills=[CAPABILITIES],
        runtime=toolkit.runtime(provider="python-runtime"),
    )
    extra = System("extra", Sequence((Action("pass", lambda d: d),)))
    pipeline = raw.pipeline(extra)
    assert isinstance(pipeline, toolkit.CompiledSystem) and pipeline.units[0] is raw
    assert not hasattr(raw, "compile")
    graph = toolkit.graph(
        engine="portable",
        nodes={"x": lambda d: {"value": 4}},
        edges=[("START", "x"), ("x", "END")],
    )
    assert isinstance(graph.run({}), dict)
    builder = toolkit.system().graph(name="legacy")
    builder.add_node("x", lambda d: {"value": 4}).edge("START", "x").edge("x", "END")
    native = builder.compile()
    assert callable(native.invoke) and not hasattr(native, "run")


def test_no_stale_compilation_and_recursive_definitions_rejected():
    original = build()
    old = original.compile()
    changed = replace(
        original, flow=Sequence((Action("new", lambda d: {"value": 100}),))
    )
    assert old.run({"value": 3}).data == {"value": 8}
    assert changed.run({"value": 3}).data == {"value": 100}
    with pytest.raises(TypeError, match="immutable"):
        Agent("bad", Sequence([Action("x", lambda d: d)])).compile()
    recursive = Agent("recursive", None)
    object.__setattr__(recursive, "flow", Sequence((recursive,)))
    with pytest.raises(ValueError, match="Recursive"):
        recursive.compile()


def test_invalid_backend_routing_skills_and_state_fail_closed():
    with pytest.raises(ValueError, match="backend"):
        replace(build(), backend="auto").compile()
    with pytest.raises(KeyError):
        Agent("missing", Action("unknown", "not_in_skill")).compile()
    first = toolkit.skill(
        name="a", tools=[toolkit.tool(name="same")(lambda x: {"x": x})]
    )
    second = toolkit.skill(
        name="b", tools=[toolkit.tool(name="same")(lambda x: {"x": x + 1})]
    )
    with pytest.raises(ValueError, match="Conflicting"):
        Agent("collision", Action("x", "same"), skills=(first, second)).compile()
    invalid = Graph(
        nodes=(("a", Action("a", lambda d: d)),),
        edges=(("a", Route(lambda d: "foreign", ("END",))),),
        start="a",
    )
    assert not Agent("route", invalid).run({}).ok
    assert not build().run({"value": object()}).ok


def test_network_and_subprocess_guard_is_active():
    with socket.socket() as sock:
        with pytest.raises(RuntimeError, match="Offline prototype"):
            sock.connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="Offline prototype"):
        subprocess.run(
            [sys.executable, "-c", "raise AssertionError('must not launch')"],
            check=True,
        )


def test_missing_langgraph_does_not_fallback(monkeypatch):
    import builtins

    original = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == "langgraph.graph":
            raise ImportError("controlled missing SDK")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    with pytest.raises(ImportError, match="missing SDK"):
        build(backend="langgraph").compile()
    assert build(backend="native").run({"value": 3}).ok


def test_eval_rejects_unknown_expectations_and_json_type_mismatch():
    with pytest.raises(ValueError, match="expected ok/data"):
        Eval(
            "unknown",
            build(),
            ({"input": {"value": 3}, "expected": {"ignored_key": True}},),
        ).compile()
    data = Agent("bool", Action("return", lambda d: {"value": True}))
    assert (
        not Eval("typed", data, ({"input": {}, "expected": {"data": {"value": 1}}},))
        .run()
        .ok
    )


def test_async_direct_and_compiled_share_the_same_data_contract():
    unit = build("Agent", "parallel", "langgraph")
    direct = asyncio.run(unit.arun({"value": 3}))
    explicit = asyncio.run(unit.compile().arun({"value": 3}))
    assert direct.ok and explicit.ok and direct.data == explicit.data == {"value": 10}


@pytest.mark.parametrize("owner", ["Agent", "System"])
@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("value, expected, event_names", [
    (3, 8, ["increment", "double"]),
    (-3, -2, ["increment"]),
    (-1, 0, ["increment", "double"]),
])
def test_direct_decisions_match_legacy_route_and_preserve_path(
    owner, backend, value, expected, event_names
):
    direct = build(owner, "graph", backend)
    choose = dict(direct.flow.edges)["increase"]
    legacy = replace(direct, flow=replace(direct.flow, edges=(
        ("increase", Route(choose, ("multiply", "END"))),
        ("multiply", "END"),
    )))
    payload = {"value": value}
    actual = direct.run(payload)
    original = legacy.run(payload)
    assert actual.ok and original.ok
    assert actual.data == original.data == {"value": expected}
    assert payload == {"value": value}
    assert [e.name for n in actual.walk() for e in n.tool_events] == event_names
    assert next(n.meta["next"] for n in actual.walk()
                if n.meta.get("graph_node") == "increase") == (
        "multiply" if value + 1 >= 0 else "END"
    )
    assert_tree(actual)
    if owner == "System":
        agents = [n.meta["name"] for n in actual.walk()
                  if n.meta.get("prototype_kind") == "agent"]
        assert agents == (["incrementer", "doubler"] if value + 1 >= 0 else ["incrementer"])


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("target", ["missing", None, ["END"], 1])
def test_invalid_direct_destination_fails_and_keeps_completed_tool(backend, target):
    calls = []

    def invalid(data):
        calls.append(data)
        data["value"] = 999  # The router receives an isolated snapshot.
        return target

    unit = Agent("invalid", Graph(
        nodes=(("increase", Action("increase", "increment")),),
        edges=(("increase", invalid),), start="increase",
    ), backend=backend, skills=(CAPABILITIES,))
    prepared = unit.compile()
    assert calls == []
    output = prepared.run({"value": 3})
    assert not output.ok and len(calls) == 1
    assert output.data == {"value": 4}
    assert any("undeclared target" in str(n.errors) for n in output.walk())
    assert [e.name for n in output.walk() for e in n.tool_events] == ["increment"]
    assert_tree(output)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_direct_router_exception_keeps_prior_result_and_skips_next_node(backend):
    unit = build("System", "graph", backend)

    def fail(data):
        raise RuntimeError("controlled decision failure")

    unit = replace(unit, flow=replace(unit.flow, edges=(
        ("increase", fail), ("multiply", "END"),
    )))
    output = unit.run({"value": 3})
    assert not output.ok and output.data == {"value": 4}
    assert any("controlled decision failure" in str(n.errors) for n in output.walk())
    assert [e.name for n in output.walk() for e in n.tool_events] == ["increment"]
    assert_tree(output)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_legacy_route_still_restricts_declared_destinations(backend):
    unit = build("Agent", "graph", backend)
    assert unit.run({"value": 3}).ok
    restricted = replace(unit, flow=replace(unit.flow, edges=(
        ("increase", Route(lambda d: "multiply", ("END",))),
        ("multiply", "END"),
    )))
    assert not restricted.run({"value": 3}).ok
    with pytest.raises(TypeError, match="destination name or callable"):
        replace(unit, flow=replace(unit.flow, edges=(
            ("increase", 123), ("multiply", "END"),
        ))).compile()
