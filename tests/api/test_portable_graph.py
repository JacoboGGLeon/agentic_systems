from __future__ import annotations

import asyncio

import pytest

import agentic_systems as toolkit
from agentic_systems.errors import GraphContractError


def test_portable_graph_runs_sequential_nodes_and_merges_state():
    app = toolkit.graph(
        engine="portable",
        nodes={
            "double": lambda state: {"value": state["value"] * 2},
            "label": lambda state: {"label": f"value={state['value']}"},
        },
        edges=[("START", "double"), ("double", "label"), ("label", "END")],
    )

    assert app.engine == "portable"
    assert app.run({"value": 3}) == {"value": 6, "label": "value=6"}


def test_portable_graph_supports_conditional_routes():
    app = toolkit.graph(
        engine="portable",
        nodes={
            "route": lambda state: {},
            "positive": lambda state: {"sign": "positive"},
            "other": lambda state: {"sign": "other"},
        },
        edges=[("START", "route"), ("positive", "END"), ("other", "END")],
        conditional_edges=[
            ("route", lambda state: "yes" if state["value"] > 0 else "no", {"yes": "positive", "no": "other"})
        ],
    )

    assert app.run({"value": 1})["sign"] == "positive"
    assert app.run({"value": 0})["sign"] == "other"


def test_portable_graph_supports_async_nodes():
    async def async_node(state):
        await asyncio.sleep(0)
        return {"value": state["value"] + 1}

    app = toolkit.graph(
        engine="portable",
        nodes={"increment": async_node},
        edges=[("START", "increment"), ("increment", "END")],
    )

    assert asyncio.run(app.arun({"value": 1}))["value"] == 2
    with pytest.raises(TypeError, match="requires await"):
        app.run({"value": 1})


def test_portable_graph_rejects_implicit_parallel_branch():
    app = toolkit.graph(
        engine="portable",
        nodes={"root": lambda state: {}, "a": lambda state: {}, "b": lambda state: {}},
        edges=[("START", "root"), ("root", "a"), ("root", "b")],
    )

    with pytest.raises(GraphContractError, match="parallel branches"):
        app.run({})


def test_auto_graph_falls_back_when_langgraph_is_unavailable(monkeypatch):
    import agentic_systems.integrations.langgraph as module

    def missing():
        raise ImportError("missing")

    monkeypatch.setattr(module, "_import_langgraph_graph", missing)
    app = toolkit.graph(
        nodes={"node": lambda state: {"ok": True}},
        edges=[("START", "node"), ("node", "END")],
    )

    assert app.engine == "portable"
    assert app.run({})["ok"] is True


def test_portable_graph_declares_native_boundary_metadata():
    app = toolkit.graph(
        engine="portable",
        nodes={"node": lambda state: {}},
        edges=[("START", "node"), ("node", "END")],
    )

    assert app.graph_kind == "agentic-systems-native"
    assert app.framework is None


def test_portable_graph_validates_nodes_and_start_contract():
    with pytest.raises(TypeError, match="must be callable"):
        toolkit.graph(
            engine="portable",
            nodes={"node": object()},
            edges=[("START", "node")],
        )

    no_start = toolkit.graph(engine="portable", nodes={}, edges=[])
    with pytest.raises(GraphContractError, match="exactly one START"):
        no_start.run({})

    two_starts = toolkit.graph(
        engine="portable",
        nodes={"a": lambda state: {}, "b": lambda state: {}},
        edges=[("START", "a"), ("START", "b")],
    )
    with pytest.raises(GraphContractError, match="exactly one START"):
        two_starts.run({})


def test_portable_graph_state_merge_variants_and_implicit_end():
    unchanged = toolkit.graph(
        engine="portable",
        nodes={"node": lambda state: None},
        edges=[("START", "node")],
    )
    assert unchanged.run({"value": 1}) == {"value": 1}

    replaced = toolkit.graph(
        engine="portable",
        nodes={"node": lambda state: state + 1},
        edges=[("START", "node"), ("node", "END")],
    )
    assert replaced.run(1) == 2


def test_portable_graph_validates_conditional_contracts():
    duplicate = toolkit.graph(
        engine="portable",
        nodes={"route": lambda state: {}},
        edges=[("START", "route")],
        conditional_edges=[
            ("route", lambda state: "END"),
            ("route", lambda state: "END"),
        ],
    )
    with pytest.raises(GraphContractError, match="one conditional router"):
        duplicate.run({})

    non_callable = toolkit.graph(
        engine="portable",
        nodes={"route": lambda state: {}},
        edges=[("START", "route")],
        conditional_edges=[("route", "END")],
    )
    with pytest.raises(TypeError, match="Each conditional edge"):
        non_callable.run({})

    invalid_map = toolkit.graph(
        engine="portable",
        nodes={"route": lambda state: {}},
        edges=[("START", "route")],
        conditional_edges=[("route", lambda state: "done", ["END"])],
    )
    with pytest.raises(TypeError, match="path_map"):
        invalid_map.run({})

    missing_route = toolkit.graph(
        engine="portable",
        nodes={"route": lambda state: {}},
        edges=[("START", "route")],
        conditional_edges=[("route", lambda state: "missing", {"done": "END"})],
    )
    with pytest.raises(GraphContractError, match="not present"):
        missing_route.run({})

    direct_route = toolkit.graph(
        engine="portable",
        nodes={"route": lambda state: {}, "finish": lambda state: {"done": True}},
        edges=[("START", "route"), ("finish", "END")],
        conditional_edges=[("route", lambda state: "finish")],
    )
    assert direct_route.run({})["done"] is True


def test_portable_graph_reports_unknown_nodes_sync_and_async():
    app = toolkit.graph(
        engine="portable",
        nodes={},
        edges=[("START", "missing")],
    )

    with pytest.raises(GraphContractError, match="unknown node"):
        app.run({})
    with pytest.raises(GraphContractError, match="unknown node"):
        asyncio.run(app.arun({}))


def test_portable_graph_cycle_safety_sync_and_async():
    app = toolkit.graph(
        engine="portable",
        nodes={"loop": lambda state: {}},
        edges=[("START", "loop"), ("loop", "loop")],
    )

    with pytest.raises(GraphContractError, match="cycle safety"):
        app.run({})
    with pytest.raises(GraphContractError, match="cycle safety"):
        asyncio.run(app.arun({}))


def test_explicit_langgraph_engine_does_not_fallback(monkeypatch):
    import agentic_systems.integrations.langgraph as module

    def missing():
        raise ImportError("missing")

    monkeypatch.setattr(module, "_import_langgraph_graph", missing)
    with pytest.raises(ImportError, match="missing"):
        toolkit.graph(engine="langgraph")