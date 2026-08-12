"""Optional LangGraph integration for Agentic Systems.

This module contains integration helpers only. Importing it does not import
LangGraph; the optional dependency is resolved at the call site that needs a
native ``StateGraph``. The core execution engines stay independent from
LangGraph, which acts only as an orchestration layer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import inspect
import warnings
from typing import Any

from agentic_systems.errors import GraphContractError
from agentic_systems.engines.names import LANGGRAPH_ORCHESTRATOR
from agentic_systems.environments import PlannedAgentGraph
from agentic_systems.results import RunResult
from agentic_systems.utils import agent_output_mapper

LangGraphState = dict[str, Any]
StateInput = str | Callable[[LangGraphState], Any]
NodeOutput = str | Callable[[RunResult, LangGraphState], Mapping[str, Any]] | None

_LANGGRAPH_INSTALL_HINT = (
    "Install with: pip install -e '.[langgraph]' or pip install langgraph"
)


def _import_langgraph_graph() -> tuple[Any, Any, Any]:
    """Return LangGraph graph primitives or raise a user-facing error."""

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*allowed_objects.*")
            graph_module = __import__(
                "langgraph.graph", fromlist=["StateGraph", "START", "END"]
            )
        StateGraph = getattr(graph_module, "StateGraph")
        START = getattr(graph_module, "START", "__start__")
        END = getattr(graph_module, "END", "__end__")
    except (
        Exception
    ) as exc:  # pragma: no cover - exercised when optional dependency is absent
        raise ImportError(
            "LangGraph integration requires the optional 'langgraph' dependency. "
            f"{_LANGGRAPH_INSTALL_HINT}."
        ) from exc
    return START, END, StateGraph


def _validate_node_name(node_name: str, *, parameter: str = "node_name") -> str:
    text = str(node_name or "").strip()
    if not text:
        raise ValueError(f"{parameter} must be a non-empty string.")
    return text


def _read_state_input(state: LangGraphState, input: StateInput) -> Any:
    if callable(input):
        return input(state)
    if input not in state:
        raise GraphContractError(
            f"input key {input!r} not found in LangGraph state. Available keys: {sorted(state.keys())}. "
            "Fix: pass input='<existing_key>' or input=lambda state: ..."
        )
    return state[input]


def _compact_trace(result: Any) -> Any:
    return result.trace("compact") if hasattr(result, "trace") else result


def _json_result(result: Any) -> Any:
    if hasattr(result, "to_dict"):
        payload = result.to_dict()
        if hasattr(result, "normalized") and isinstance(payload, dict):
            payload.setdefault("normalized", result.normalized())
        if hasattr(result, "trace") and isinstance(payload, dict):
            payload.setdefault("compact", result.trace("compact"))
        return payload
    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="json")
        if hasattr(result, "normalized") and isinstance(payload, dict):
            payload.setdefault("normalized", result.normalized())
        return payload
    return result


def _result_text(result: Any) -> Any:
    return getattr(result, "text", result)


def _map_node_update(
    result: Any,
    state: LangGraphState,
    *,
    output: NodeOutput,
    trace: str | None,
    result_key: str | None,
) -> dict[str, Any]:
    update: dict[str, Any] = {}
    if callable(output):
        mapped = output(result, state)
        if not isinstance(mapped, Mapping):
            raise TypeError("Custom LangGraph output mapper must return a mapping.")
        update.update(dict(mapped))
    elif output is not None:
        update[str(output)] = _result_text(result)

    if result_key is not None:
        projected = _json_result(result)
        if isinstance(projected, Mapping):
            projected = dict(projected)
            meta = dict(projected.get("meta") or {})
            meta["framework_adapter"] = LANGGRAPH_ORCHESTRATOR
            projected["meta"] = meta
        update[str(result_key)] = projected
    if trace is not None:
        update[str(trace)] = _compact_trace(result)
    return update


def _call_agent_node_factory(factory: Callable[..., Any], **kwargs: Any) -> Any:
    """Call an existing node factory without assuming its exact signature."""

    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):  # pragma: no cover - uncommon C-extension callables
        return factory(**kwargs)
    if any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return factory(**kwargs)
    accepted = {
        key: value for key, value in kwargs.items() if key in signature.parameters
    }
    return factory(**accepted)


def _short_text(value: Any, *, max_chars: int = 320) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def _public_payload_summary(payload: Mapping[str, Any]) -> str:
    """Return a human-friendly fallback for structured graph answers.

    LangGraph states often store the trustworthy answer as a business dict, for
    example ``{"resultado_numérico": 42, "color": "azul"}``. The lineage
    adapter must not ignore that dict and fall back to free-form intermediate
    agent text. This helper keeps the adapter generic: it summarizes scalar
    public fields without knowing a specific domain.
    """

    items: list[str] = []
    for key, value in payload.items():
        if key.startswith("_") or key in {"raw", "metadata", "meta", "trace", "steps"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            items.append(f"{key}: {value}")
    return "; ".join(items)


def _tool_output_payload(tool: Mapping[str, Any]) -> dict[str, Any]:
    output = tool.get("output") if isinstance(tool.get("output"), Mapping) else {}
    data = output.get("data") if isinstance(output.get("data"), Mapping) else {}
    return dict(data or output)


def _tool_facts(tool: Mapping[str, Any]) -> dict[str, Any]:
    """Compact tool facts for lineage evidence.

    Avoid dumping full provider envelopes into the human evidence section. Keep
    the pieces that explain the computation: tool name, status, input and
    business output.
    """

    facts: dict[str, Any] = {}
    name = tool.get("name") or tool.get("tool")
    if name:
        facts["tool"] = name
    if "ok" in tool:
        facts["ok"] = tool.get("ok")
    if isinstance(tool.get("input"), Mapping):
        facts["input"] = dict(tool.get("input") or {})
    payload = _tool_output_payload(tool)
    for key in (
        "operation",
        "result",
        "number",
        "text",
        "summary",
        "message",
        "row_count",
        "n_rows",
        "route",
        "query_id",
    ):
        if key in payload:
            facts[key] = payload[key]
    rows = payload.get("rows")
    if isinstance(rows, list):
        facts["row_count"] = (
            payload.get("row_count") or payload.get("n_rows") or len(rows)
        )
        facts["sample_rows"] = rows[:3]
    return facts


def _mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "normalized"):
        return value.normalized()
    if hasattr(value, "trace"):
        return value.trace("compact")
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
        return dict(payload) if isinstance(payload, Mapping) else {"value": payload}
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json")
        return dict(payload) if isinstance(payload, Mapping) else {"value": payload}
    return dict(value) if isinstance(value, Mapping) else {"value": value}


def _answer_from_payload(payload: Mapping[str, Any]) -> str:
    for key in (
        "final_answer",
        "answer",
        "output",
        "result",
        "text",
        "message",
        "summary",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, Mapping):
            nested = _answer_from_payload(value)
            if nested:
                return nested
    answer = payload.get("answer") if isinstance(payload.get("answer"), Mapping) else {}
    data = answer.get("data") if isinstance(answer.get("data"), Mapping) else {}
    for key in ("summary", "text", "message", "error"):
        value = data.get(key)
        if value:
            return str(value)
    summary = _public_payload_summary(payload)
    return summary


def _run_tools(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[Any] = []
    if isinstance(payload.get("tools"), list):
        candidates = list(payload.get("tools") or [])
    elif isinstance(payload.get("tool_events"), list):
        candidates = list(payload.get("tool_events") or [])
    elif isinstance(payload.get("normalized"), Mapping) and isinstance(
        payload["normalized"].get("tools"), list
    ):
        candidates = list(payload["normalized"].get("tools") or [])
    blocks = payload.get("blocks") if isinstance(payload.get("blocks"), Mapping) else {}
    if not candidates and isinstance(blocks.get("tool_actions"), list):
        candidates = list(blocks.get("tool_actions") or [])
    tools: list[dict[str, Any]] = []
    for item in candidates:
        if isinstance(item, Mapping):
            tools.append(dict(item))
        elif hasattr(item, "model_dump"):
            dumped = item.model_dump(mode="json")
            if isinstance(dumped, Mapping):
                tools.append(dict(dumped))
    return tools


def _tool_summary(tool: Mapping[str, Any]) -> str:
    for key in ("summary", "message", "text"):
        value = tool.get(key)
        if value:
            return str(value)
    output = tool.get("output") if isinstance(tool.get("output"), Mapping) else {}
    for key in ("summary", "message", "text", "error"):
        value = output.get(key)
        if value:
            return str(value)
    facts = _tool_facts(tool)
    name = facts.get("tool") or tool.get("name") or tool.get("tool") or "tool"
    if "operation" in facts and "result" in facts:
        return f"{name}: {facts['operation']} -> {facts['result']}"
    if "result" in facts:
        return f"{name}: resultado {facts['result']}"
    if "text" in facts and "number" in facts:
        return f"{name}: {facts['number']} -> {facts['text']}"
    row_count = (
        facts.get("row_count") or output.get("row_count") or output.get("n_rows")
    )
    if row_count is not None:
        return f"{name} executed and returned {row_count} row(s)."
    return f"{name} executed."


def _trace_payloads_from_state(
    state: Mapping[str, Any], *, trace_keys: Iterable[str] | None = None
) -> list[tuple[str, dict[str, Any]]]:
    explicit = tuple(trace_keys or ("ada_trace", "trace", "lineage_trace"))
    payloads: list[tuple[str, dict[str, Any]]] = []
    for key, value in state.items():
        key_text = str(key)
        looks_like_trace_key = (
            key_text in explicit
            or key_text.endswith("_trace")
            or key_text.endswith("_result")
            or key_text in {"result"}
        )
        if not looks_like_trace_key:
            continue
        payload = _mapping(value)
        if any(
            marker in payload
            for marker in (
                "normalized",
                "tool_events",
                "tools",
                "blocks",
                "trace_schema_version",
                "answer",
            )
        ):
            payloads.append((key_text, payload))
    return payloads


def lineage_from_langgraph_state(
    state: Mapping[str, Any],
    *,
    name: str = "langgraph.run",
    question: str | None = None,
    goal: str = "",
    answer_keys: Iterable[str] = ("final_answer", "answer", "output", "result"),
    trace_keys: Iterable[str] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Build ``LineageMemory`` from a LangGraph final state.

    The adapter is pure projection: it does not import LangGraph and does not
    execute the graph. It reads the final state produced by graph nodes and
    turns node outputs, run traces and validation payloads into the shared
    Lineage Memory format.
    """

    from agentic_systems.lineage import LineageMemory, LineageStep

    if not isinstance(state, Mapping):
        raise TypeError(
            "lineage_from_langgraph_state(...) expects a mapping-like graph state."
        )

    state_dict = dict(state)
    resolved_question = (
        question
        if question is not None
        else str(state_dict.get("prompt") or state_dict.get("user_prompt") or "")
    )
    answer = ""
    for key in answer_keys:
        value = state_dict.get(str(key))
        if isinstance(value, str) and value.strip():
            answer = value.strip()
            break
        if isinstance(value, Mapping):
            answer = _answer_from_payload(value)
            if answer:
                break
    if not answer:
        for _key, payload in _trace_payloads_from_state(
            state_dict, trace_keys=trace_keys
        ):
            answer = _answer_from_payload(payload)
            if answer:
                break

    steps = [
        LineageStep(
            step_id="input",
            kind="input",
            title="Graph input received",
            summary=_short_text(resolved_question, max_chars=280)
            or "No graph input text recorded.",
            source="langgraph.state",
            why="Esta es la entrada que inició la ejecución del grafo.",
            evidence={"state_keys": sorted(map(str, state_dict.keys()))},
        )
    ]

    plan = (
        state_dict.get("plan") if isinstance(state_dict.get("plan"), Mapping) else None
    )
    if plan:
        route = plan.get("route") or state_dict.get("route")
        reason = str(plan.get("reason") or "The graph produced a routing plan.").strip()
        if route not in (None, "", "None", "none"):
            summary = f"route={route}; {reason}"
        else:
            summary = reason
        steps.append(
            LineageStep(
                step_id="decision_plan",
                kind="decision",
                title="Graph routing decision",
                summary=_short_text(summary, max_chars=360),
                source="langgraph.state.plan",
                why="El grafo registró la ruta o plan antes de ejecutar el nodo de trabajo.",
                evidence={"plan": dict(plan)},
            )
        )

    trace_payloads = _trace_payloads_from_state(state_dict, trace_keys=trace_keys)
    for index, (key, payload) in enumerate(trace_payloads, start=1):
        tools_for_node = _run_tools(payload)
        if tools_for_node:
            summaries = [_tool_summary(tool) for tool in tools_for_node]
            node_summary = f"{key}: " + "; ".join(
                summary for summary in summaries if summary
            )
        else:
            node_summary = (
                _answer_from_payload(payload) or f"State payload {key} recorded."
            )
        steps.append(
            LineageStep(
                step_id=f"node_{index}",
                kind="decision",
                title=f"Graph node: {key}",
                summary=_short_text(node_summary, max_chars=420),
                source=key,
                why="El nodo dejó salida estructurada para auditoría.",
                evidence={
                    "engine": payload.get("engine")
                    or payload.get("runtime", {}).get("engine")
                    if isinstance(payload.get("runtime"), Mapping)
                    else payload.get("engine"),
                    "model": payload.get("model"),
                    "ok": payload.get("run_ok", payload.get("ok")),
                },
            )
        )
        for tool_index, tool in enumerate(tools_for_node, start=1):
            steps.append(
                LineageStep(
                    step_id=f"node_{index}_tool_{tool_index}",
                    kind="tool",
                    title=f"Tool: {tool.get('name') or tool.get('tool') or 'tool'}",
                    summary=_short_text(_tool_summary(tool), max_chars=360),
                    source=str(tool.get("name") or tool.get("tool") or key),
                    why="La tool del grafo dejó salida estructurada para soportar la respuesta.",
                    evidence={"facts": _tool_facts(tool)},
                )
            )
        validation = payload.get("validation") or state_dict.get("graph_validation")
        if isinstance(validation, Mapping):
            steps.append(
                LineageStep(
                    step_id=f"node_{index}_validation",
                    kind="validation",
                    title="Graph validation",
                    summary="Graph validation passed."
                    if validation.get("ok", True)
                    else "Graph validation reported issues.",
                    source=str(validation.get("node") or key),
                    why="La validación del grafo conserva lo esperado y lo ejecutado.",
                    evidence={"validation": dict(validation)},
                )
            )

    graph_validation = (
        state_dict.get("graph_validation")
        if isinstance(state_dict.get("graph_validation"), Mapping)
        else None
    )
    if graph_validation and not any(
        step.step_id.endswith("validation") for step in steps
    ):
        steps.append(
            LineageStep(
                step_id="graph_validation",
                kind="validation",
                title="Graph validation",
                summary="Graph validation passed."
                if graph_validation.get("ok", True)
                else "Graph validation reported issues.",
                source=str(
                    graph_validation.get("node") or "langgraph.state.graph_validation"
                ),
                why="La validación final confirma si la ruta esperada se ejecutó.",
                evidence={"validation": dict(graph_validation)},
            )
        )

    steps.append(
        LineageStep(
            step_id="answer",
            kind="answer",
            title="Graph final answer",
            summary=_short_text(answer, max_chars=520)
            or "No final graph answer text recorded.",
            source="langgraph.state",
            why="Esta es la respuesta final derivada del estado consolidado del grafo.",
            evidence={
                "answer": answer,
                "state_keys": sorted(map(str, state_dict.keys())),
            },
        )
    )

    return LineageMemory(
        name=name,
        question=str(resolved_question or ""),
        goal=goal,
        answer=answer,
        ok=bool(graph_validation.get("ok", True)) if graph_validation else True,
        steps=steps,
        tags=list(tags or ["integration", "langgraph"]),
        metadata={
            "integration": "langgraph",
            "state_keys": sorted(map(str, state_dict.keys())),
            **(metadata or {}),
        },
    )


def lineage_from_langgraph_result(result: Any, **kwargs: Any) -> Any:
    """Alias for graph outputs that are mapping-like final states."""

    return lineage_from_langgraph_state(_mapping(result), **kwargs)


def build_langgraph_agent_node(
    agent: Any,
    *,
    input: StateInput = "prompt",
    output: NodeOutput = agent_output_mapper,
    trace: str | None = "ada_trace",
    result_key: str | None = None,
    mode: str = "default",
    config: Any = None,
    async_node: bool = False,
) -> Callable[[LangGraphState], Any]:
    """Build a LangGraph-compatible node from an Agent-like object.

    Parameters are intentionally state-key/mapping based. Nothing in this
    helper assumes a specific business case, prompt name, output schema, tool
    name, or agent name.
    """

    if async_node:
        if not hasattr(agent, "arun"):
            if hasattr(agent, "as_async_node"):
                return _call_agent_node_factory(
                    agent.as_async_node,
                    input=input,
                    output=output,
                    trace=trace,
                    result_key=result_key,
                    mode=mode,
                    config=config,
                )
            raise TypeError(
                "async_node=True requires an agent exposing arun(...) or as_async_node(...)."
            )

        async def _async_node(state: LangGraphState) -> dict[str, Any]:
            prompt = _read_state_input(state, input)
            result = await agent.arun(prompt, mode=mode, config=config)
            return _map_node_update(
                result, state, output=output, trace=trace, result_key=result_key
            )

        return _async_node

    if not hasattr(agent, "run"):
        if hasattr(agent, "as_node"):
            return _call_agent_node_factory(
                agent.as_node,
                input=input,
                output=output,
                trace=trace,
                result_key=result_key,
                mode=mode,
                config=config,
            )
        raise TypeError(
            "build_langgraph_agent_node expects an agent exposing run(...) or as_node(...)."
        )

    def _node(state: LangGraphState) -> dict[str, Any]:
        prompt = _read_state_input(state, input)
        result = agent.run(prompt, mode=mode, config=config)
        return _map_node_update(
            result, state, output=output, trace=trace, result_key=result_key
        )

    return _node


def agent_node(
    agent: Any,
    *,
    input: StateInput = "prompt",
    result_key: str = "result",
    output: NodeOutput = None,
    trace: str | None = None,
    mode: str = "eval",
    config: Any = None,
    async_node: bool = False,
) -> Callable[[LangGraphState], Any]:
    """Create a graph node from an Agentic Systems agent.

    This is the user-facing helper for tutorials and product code. It keeps the
    notebook mental model at ``state -> node -> state`` while the lower-level
    LangGraph adapter remains available for advanced integrations.
    """

    return build_langgraph_agent_node(
        agent,
        input=input,
        output=output,
        trace=trace,
        result_key=result_key,
        mode=mode,
        config=config,
        async_node=async_node,
    )


class GraphApp:
    """Thin Agentic Systems wrapper around a compiled graph backend."""

    graph_kind = "graph-app"
    framework = None

    def __init__(self, *, native: Any, engine: str, name: str = "graph") -> None:
        self.native = native
        self.engine = engine
        self.name = name
        self.graph_kind = (
            "framework-native" if engine == "langgraph" else "agentic-systems-native"
        )
        self.framework = LANGGRAPH_ORCHESTRATOR if engine == "langgraph" else None

    def run(self, state: Any) -> Any:
        """Run the compiled graph with a user state object or mapping."""

        if hasattr(self.native, "invoke"):
            return self.native.invoke(state)
        raise TypeError("Compiled graph object must expose invoke(state).")

    async def arun(self, state: Any) -> Any:
        """Run the compiled graph asynchronously when supported."""

        if hasattr(self.native, "ainvoke"):
            return await self.native.ainvoke(state)
        return self.run(state)

    def invoke(self, state: Any) -> Any:
        return self.run(state)

    def lineage(self, state_or_result: Any, **kwargs: Any) -> Any:
        """Project a graph input/result state into Lineage Memory."""

        if isinstance(state_or_result, Mapping):
            state = dict(state_or_result)
        else:
            state = self.run(state_or_result)
        kwargs.setdefault("name", self.name)
        return lineage_from_langgraph_state(state, **kwargs)


class _PortableGraph:
    """Dependency-free backend for the portable ``graph`` contract."""

    def __init__(self, *, nodes, edges, conditional_edges) -> None:
        self.nodes = dict(nodes)
        self.edges = [(str(source), str(target)) for source, target in edges]
        self.conditional_edges = list(conditional_edges)
        for name, node in self.nodes.items():
            _validate_node_name(name, parameter="node name")
            if not callable(node):
                raise TypeError(f"Graph node {name!r} must be callable.")

    @staticmethod
    def _merge_state(state: Any, update: Any) -> Any:
        if update is None:
            return state
        if isinstance(state, Mapping) and isinstance(update, Mapping):
            return {**dict(state), **dict(update)}
        return update

    def _conditional_target(self, source: str, state: Any) -> str | None:
        matches = [item for item in self.conditional_edges if str(item[0]) == source]
        if len(matches) > 1:
            raise GraphContractError(
                f"Portable graph supports one conditional router per node; got {source!r} twice."
            )
        if not matches:
            return None
        item = matches[0]
        if len(item) not in {2, 3} or not callable(item[1]):
            raise TypeError(
                "Each conditional edge must be (source, route_fn) or (source, route_fn, path_map)."
            )
        route = str(item[1](state))
        if len(item) == 3:
            path_map = item[2]
            if not isinstance(path_map, Mapping):
                raise TypeError(
                    "conditional edge path_map must be a mapping of route -> node name."
                )
            if route not in path_map:
                raise GraphContractError(
                    f"Conditional route {route!r} is not present in path_map."
                )
            return str(path_map[route])
        return route

    def _next_target(self, source: str, state: Any) -> str:
        conditional = self._conditional_target(source, state)
        if conditional is not None:
            return conditional
        targets = [
            target for edge_source, target in self.edges if edge_source == source
        ]
        if not targets:
            return "END"
        if len(targets) > 1:
            raise GraphContractError(
                f"Portable graph does not execute parallel branches from {source!r}; "
                "use conditional_edges or engine='langgraph'."
            )
        return targets[0]

    def _start_target(self) -> str:
        starts = [target for source, target in self.edges if source.upper() == "START"]
        if len(starts) != 1:
            raise GraphContractError("Portable graph requires exactly one START edge.")
        return starts[0]

    def invoke(self, state: Any) -> Any:
        current = self._start_target()
        result = dict(state) if isinstance(state, Mapping) else state
        steps = 0
        step_limit = max(100, len(self.nodes) * 10)
        while current.upper() != "END":
            if current not in self.nodes:
                raise GraphContractError(f"Graph references unknown node {current!r}.")
            update = self.nodes[current](result)
            if inspect.isawaitable(update):
                if inspect.iscoroutine(update):
                    update.close()
                raise TypeError("Async graph node requires await graph.arun(state).")
            result = self._merge_state(result, update)
            current = self._next_target(current, result)
            steps += 1
            if steps > step_limit:
                raise GraphContractError(
                    "Portable graph exceeded its cycle safety limit."
                )
        return result

    async def ainvoke(self, state: Any) -> Any:
        current = self._start_target()
        result = dict(state) if isinstance(state, Mapping) else state
        steps = 0
        step_limit = max(100, len(self.nodes) * 10)
        while current.upper() != "END":
            if current not in self.nodes:
                raise GraphContractError(f"Graph references unknown node {current!r}.")
            update = self.nodes[current](result)
            if inspect.isawaitable(update):
                update = await update
            result = self._merge_state(result, update)
            current = self._next_target(current, result)
            steps += 1
            if steps > step_limit:
                raise GraphContractError(
                    "Portable graph exceeded its cycle safety limit."
                )
        return result


def _edge_endpoint(value: str, *, start: Any, end: Any) -> Any:
    text = str(value)
    if text.upper() == "START":
        return start
    if text.upper() == "END":
        return end
    return text


def _normalize_conditional_path_map(
    path_map: Mapping[str, str] | None, *, start: Any, end: Any
) -> dict[str, Any] | None:
    if path_map is None:
        return None
    if not isinstance(path_map, Mapping):
        raise TypeError(
            "conditional edge path_map must be a mapping of route -> node name."
        )
    return {
        str(route): _edge_endpoint(target, start=start, end=end)
        for route, target in path_map.items()
    }


def graph(
    *,
    state: Any = dict,
    nodes: Mapping[str, Callable[[LangGraphState], Any]] | None = None,
    edges: Iterable[tuple[str, str]] | None = None,
    conditional_edges: Iterable[
        tuple[str, Callable[[LangGraphState], str]]
        | tuple[str, Callable[[LangGraphState], str], Mapping[str, str]]
    ]
    | None = None,
    engine: str = "auto",
    name: str = "graph",
    compile_graph: bool = True,
) -> Any:
    """Build a graph from portable state, nodes and edges.

    ``engine='auto'`` uses native LangGraph when installed and otherwise the
    dependency-free portable backend. ``engine='portable'`` forces the portable
    subset; ``engine='langgraph'`` explicitly requires LangGraph. For routers,
    pass ``conditional_edges=[('router', route_fn, {'a': 'node_a', 'b': 'END'})]``.
    """

    resolved_engine = str(engine).strip().lower().replace("_", "-")
    if resolved_engine not in {"auto", "portable", "langgraph"}:
        raise ValueError(
            "graph(..., engine=...) supports 'auto', 'portable' or 'langgraph'."
        )
    node_map = dict(nodes or {})
    edge_list = list(edges or [])
    conditional_list = list(conditional_edges or [])
    if resolved_engine == "portable":
        native = _PortableGraph(
            nodes=node_map, edges=edge_list, conditional_edges=conditional_list
        )
        return GraphApp(native=native, engine="portable", name=name)
    try:
        START, END, StateGraph = _import_langgraph_graph()
    except ImportError:
        if resolved_engine == "langgraph":
            raise
        native = _PortableGraph(
            nodes=node_map, edges=edge_list, conditional_edges=conditional_list
        )
        return GraphApp(native=native, engine="portable", name=name)
    native = StateGraph(state)
    for node_name, node in node_map.items():
        native.add_node(_validate_node_name(node_name, parameter="node name"), node)
    for edge_start, edge_end in edge_list:
        native.add_edge(
            _edge_endpoint(edge_start, start=START, end=END),
            _edge_endpoint(edge_end, start=START, end=END),
        )
    for item in conditional_list:
        if not isinstance(item, tuple) or len(item) not in {2, 3}:
            raise TypeError(
                "Each conditional edge must be (source, route_fn) or (source, route_fn, path_map)."
            )
        source = _edge_endpoint(item[0], start=START, end=END)
        route_fn = item[1]
        if not callable(route_fn):
            raise TypeError("conditional edge route_fn must be callable.")
        path_map = (
            _normalize_conditional_path_map(item[2], start=START, end=END)
            if len(item) == 3
            else None
        )
        if path_map is None:
            native.add_conditional_edges(source, route_fn)
        else:
            native.add_conditional_edges(source, route_fn, path_map)
    compiled = native.compile() if compile_graph else native
    return GraphApp(native=compiled, engine="langgraph", name=name)


def build_langgraph_agent_graph(
    agent: Any,
    *,
    node_name: str | None = None,
    state_schema: Any = dict,
    compile_graph: bool = True,
    input: StateInput = "prompt",
    output: NodeOutput = agent_output_mapper,
    trace: str | None = "ada_trace",
    result_key: str | None = None,
    mode: str = "default",
    config: Any = None,
    async_node: bool = False,
) -> Any:
    """Build a one-node native LangGraph app for an Agent-like object."""

    START, END, StateGraph = _import_langgraph_graph()
    resolved_node_name = _validate_node_name(
        node_name or getattr(agent, "name", "agent")
    )
    graph = StateGraph(state_schema)
    graph.add_node(
        resolved_node_name,
        build_langgraph_agent_node(
            agent,
            input=input,
            output=output,
            trace=trace,
            result_key=result_key,
            mode=mode,
            config=config,
            async_node=async_node,
        ),
    )
    graph.add_edge(START, resolved_node_name)
    graph.add_edge(resolved_node_name, END)
    return graph.compile() if compile_graph else graph


def _coerce_planned_graph(
    planned_graph: Any | None, agents: Mapping[str, Any] | None, kwargs: dict[str, Any]
) -> Any:
    if planned_graph is not None:
        if not hasattr(planned_graph, "invoke"):
            raise TypeError("planned_graph must expose invoke(state).")
        if agents is not None:
            raise TypeError("Pass either planned_graph=... or agents=..., not both.")
        if kwargs:
            raise TypeError(
                "Planner execution kwargs are only valid when building from agents=...."
            )
        return planned_graph
    if agents is None:
        raise TypeError(
            "build_langgraph_planned_graph requires planned_graph=... or agents=...."
        )
    return PlannedAgentGraph(agents, **kwargs)


def build_langgraph_planned_graph(
    planned_graph: Any | None = None,
    *,
    agents: Mapping[str, Any] | None = None,
    state_schema: Any = dict,
    node_name: str = "planned_step",
    compile_graph: bool = True,
    **planned_graph_kwargs: Any,
) -> Any:
    """Build a native LangGraph app around ``PlannedAgentGraph`` semantics.

    ``PlannedAgentGraph`` remains the portable internal execution contract.
    This helper wraps that contract in a native LangGraph START -> node -> END
    graph when the user explicitly wants LangGraph orchestration.
    """

    START, END, StateGraph = _import_langgraph_graph()
    graph_runner = _coerce_planned_graph(
        planned_graph, agents, dict(planned_graph_kwargs)
    )
    resolved_node_name = _validate_node_name(node_name)

    def _node(state: LangGraphState) -> dict[str, Any]:
        result = graph_runner.invoke(state)
        if not isinstance(result, dict):
            raise TypeError(
                "Planned graph LangGraph node must return a dict state update."
            )
        return result

    graph = StateGraph(state_schema)
    graph.add_node(resolved_node_name, _node)
    graph.add_edge(START, resolved_node_name)
    graph.add_edge(resolved_node_name, END)
    return graph.compile() if compile_graph else graph


class AgenticGraph:
    """Small wrapper over native LangGraph without hiding the compiled app.

    This class is intentionally thin: it helps notebooks create graph nodes from
    Agentic Systems agents, but ``native`` still exposes LangGraph directly for
    advanced users.
    """

    graph_kind = "framework-native"
    framework = LANGGRAPH_ORCHESTRATOR

    def __init__(self, *, name: str, state: Any = None) -> None:
        self.name = _validate_node_name(name, parameter="name")
        self.state = state or dict
        START, END, StateGraph = _import_langgraph_graph()
        self._start = START
        self._end = END
        self._native = StateGraph(self.state)

    @property
    def native(self) -> Any:
        return self._native

    def add_agent_node(
        self,
        name: str,
        *,
        agent: Any,
        input: StateInput = "prompt",
        output: NodeOutput = agent_output_mapper,
        trace: str | None = "ada_trace",
        result_key: str | None = None,
        async_node: bool = False,
        mode: str = "default",
        config: Any = None,
    ) -> "AgenticGraph":
        self._native.add_node(
            _validate_node_name(name, parameter="name"),
            build_langgraph_agent_node(
                agent,
                input=input,
                output=output,
                trace=trace,
                result_key=result_key,
                async_node=async_node,
                mode=mode,
                config=config,
            ),
        )
        return self

    def add_node(self, name: str, node: Any) -> "AgenticGraph":
        self._native.add_node(_validate_node_name(name, parameter="name"), node)
        return self

    def edge(self, start: str, end: str) -> "AgenticGraph":
        """Add an edge, accepting ergonomic ``START``/``END`` aliases."""

        self._native.add_edge(
            _edge_endpoint(start, start=self._start, end=self._end),
            _edge_endpoint(end, start=self._start, end=self._end),
        )
        return self

    def conditional_edges(self, *args: Any, **kwargs: Any) -> "AgenticGraph":
        self._native.add_conditional_edges(*args, **kwargs)
        return self

    def compile(self, *args: Any, **kwargs: Any) -> Any:
        return self._native.compile(*args, **kwargs)


__all__ = [
    "AgenticGraph",
    "LangGraphState",
    "GraphApp",
    "agent_node",
    "graph",
    "build_langgraph_agent_graph",
    "build_langgraph_agent_node",
    "build_langgraph_planned_graph",
    "lineage_from_langgraph_result",
    "lineage_from_langgraph_state",
]
