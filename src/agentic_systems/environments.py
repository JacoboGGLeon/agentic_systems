"""Episodic environments for Agentic Systems 1.0.

The environment API follows the Gymnasium shape without depending on
Gymnasium. Each transition delegates to any graph/system exposing the same
``invoke(state)`` contract, or to a plain transition function. This makes table-driven agent runs behave like
controlled episodes: each row is one step, memory can flow between steps, and
reward functions can evaluate the transition deterministically.
"""

from __future__ import annotations

import asyncio
import inspect
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4


GraphState = dict[str, Any]
ObservationMapper = Callable[[dict[str, Any], "AgenticEnvironment"], Any]
StateFactory = Callable[[dict[str, Any], Any, "AgenticEnvironment"], GraphState]
RewardFn = Callable[[GraphState, dict[str, Any], Any, "AgenticEnvironment"], float]
MemoryUpdater = Callable[[Any, GraphState, dict[str, Any], Any, "AgenticEnvironment"], Any]
TransitionFn = Callable[[dict[str, Any], Any, dict[str, Any]], GraphState]




class AgentStepGraph:
    """Tiny invoke(state) adapter for running one agent inside an environment.

    This graph intentionally avoids optional LangGraph dependencies. Use
    ``build_single_agent_step_graph`` when you specifically want a native
    LangGraph app; use this adapter for portable sandbox episodes.
    """

    def __init__(
        self,
        agent: Any,
        *,
        input: str | Callable[[GraphState], Any] = "row",
        output: str | Callable[[Any, GraphState], Mapping[str, Any]] | None = "agent_text",
        trace: str | None = "agent_trace",
        result_key: str | None = "agent_result",
        mode: str = "default",
        config: Any = None,
    ) -> None:
        self.agent = agent
        self.input = input
        self.output = output
        self.trace = trace
        self.result_key = result_key
        self.mode = mode
        self.config = config

    def invoke(self, state: GraphState) -> GraphState:
        prompt = _read_graph_input(state, self.input)
        result = self.agent.run(prompt, mode=self.mode, config=self.config)
        update = _map_agent_result(result, state, self.output, self.trace, self.result_key)
        return {**state, **update}


class DynamicAgentRouterGraph:
    """Environment graph that chooses one agent per step.

    Responsibility split:
    - Environment owns episode state, memory, reward and history.
    - Router owns the decision of which agent should act on the current state.
    - Agent owns one reasoning/tool-use turn after it has been selected.
    """

    def __init__(
        self,
        agents: Mapping[str, Any],
        *,
        router: Callable[[GraphState, Mapping[str, Any]], str],
        input: str | Callable[[GraphState], Any] = "row",
        selected_key: str = "selected_agent",
        output: str | Callable[[Any, GraphState], Mapping[str, Any]] | None = "agent_text",
        trace: str | None = "agent_trace",
        result_key: str | None = "agent_result",
        mode: str = "default",
        config: Any = None,
    ) -> None:
        self.agents = dict(agents)
        if not self.agents:
            raise ValueError("DynamicAgentRouterGraph requires at least one agent.")
        self.router = router
        self.input = input
        self.selected_key = selected_key
        self.output = output
        self.trace = trace
        self.result_key = result_key
        self.mode = mode
        self.config = config

    def invoke(self, state: GraphState) -> GraphState:
        selected = str(self.router(state, self.agents))
        if selected not in self.agents:
            raise KeyError(f"Router selected unknown agent {selected!r}. Available: {sorted(self.agents)}")
        agent = self.agents[selected]
        prompt = _read_graph_input(state, self.input)
        result = agent.run(prompt, mode=self.mode, config=self.config)
        update = _map_agent_result(result, state, self.output, self.trace, self.result_key)
        update[self.selected_key] = selected
        return {**state, **update}


def build_agent_step_graph(agent: Any, **kwargs: Any) -> AgentStepGraph:
    """Return a portable one-agent environment graph."""

    return AgentStepGraph(agent, **kwargs)


def build_dynamic_agent_router_graph(agents: Mapping[str, Any], **kwargs: Any) -> DynamicAgentRouterGraph:
    """Return a portable multi-agent router graph for dynamic episodes."""

    return DynamicAgentRouterGraph(agents, **kwargs)


class PlannedAgentGraph:
    """Environment graph that executes an explicit agent plan.

    A planned graph is useful when a planner has already decided the episode
    shape. Each environment record declares which agent should run and what
    input it should receive. The graph validates the selected agent and records
    the route decision alongside the agent result.
    """

    def __init__(
        self,
        agents: Mapping[str, Any],
        *,
        agent_key: str = "agent",
        input_key: str = "input",
        selected_key: str = "selected_agent",
        output: str | Callable[[Any, GraphState], Mapping[str, Any]] | None = "agent_text",
        trace: str | None = "agent_trace",
        result_key: str | None = "agent_result",
        mode: str = "default",
        config: Any = None,
    ) -> None:
        self.agents = dict(agents)
        if not self.agents:
            raise ValueError("PlannedAgentGraph requires at least one agent.")
        self.agent_key = agent_key
        self.input_key = input_key
        self.selected_key = selected_key
        self.output = output
        self.trace = trace
        self.result_key = result_key
        self.mode = mode
        self.config = config

    def invoke(self, state: GraphState) -> GraphState:
        row = state.get("row") or {}
        if not isinstance(row, Mapping):
            raise TypeError("PlannedAgentGraph expects state['row'] to be a mapping.")
        selected = str(row.get(self.agent_key) or "")
        if selected not in self.agents:
            raise KeyError(f"Plan selected unknown agent {selected!r}. Available: {sorted(self.agents)}")
        if self.input_key not in row:
            raise KeyError(f"Plan row is missing input key {self.input_key!r}.")
        agent = self.agents[selected]
        result = agent.run(row[self.input_key], mode=self.mode, config=self.config)
        update = _map_agent_result(result, state, self.output, self.trace, self.result_key)
        update[self.selected_key] = selected
        update["plan"] = {
            "step_id": row.get("step_id"),
            "agent": selected,
            "reason": row.get("reason"),
            "expected_tools": list(row.get("expected_tools") or []),
        }
        return {**state, **update}


def build_planned_agent_graph(agents: Mapping[str, Any], **kwargs: Any) -> PlannedAgentGraph:
    """Return a graph that executes row-declared agent plans.

    This is the bridge between a planner/router decision and an
    ``AgenticEnvironment`` episode: the planner chooses records, while the
    environment executes and rewards them.
    """

    return PlannedAgentGraph(agents, **kwargs)


@dataclass(frozen=True)
class EnvironmentTransition:
    """One auditable environment-agent transition."""

    episode_id: str
    step_index: int
    row: dict[str, Any]
    action: Any
    graph_state: GraphState
    reward: float
    terminated: bool
    truncated: bool
    memory: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "step_index": self.step_index,
            "row": self.row,
            "action": self.action,
            "graph_state": self.graph_state,
            "reward": self.reward,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "memory": self.memory,
        }


@dataclass
class AgenticEnvironment:
    """Gymnasium-shaped environment backed by LangGraph transitions.

    Parameters
    ----------
    records:
        A pandas DataFrame, list of dicts or any iterable of mappings. Each
        record becomes one episode step.
    graph:
        A compiled LangGraph app, an AgenticGraph, or any object exposing
        ``invoke(state)``. Passing an uncompiled object with ``compile()`` is
        also supported.
    initial_memory:
        Memory visible to every step through ``memory_key``.
    reward_fn:
        Optional deterministic reward function over the completed transition.
    state_factory:
        Optional mapper that builds the graph state for one row.
    observation_mapper:
        Optional mapper for observations returned by ``reset`` and ``step``.
    """

    records: Any
    graph: Any | None = None
    name: str = "agentic_environment"
    transition_fn: TransitionFn | None = None
    episode_id: str | None = None
    initial_memory: Any = field(default_factory=dict)
    row_key: str = "row"
    action_key: str = "action"
    memory_key: str = "memory"
    episode_key: str = "episode"
    reward_fn: RewardFn | None = None
    state_factory: StateFactory | None = None
    memory_updater: MemoryUpdater | None = None
    observation_mapper: ObservationMapper | None = None
    max_steps: int | None = None
    keep_history: bool = True
    render_mode: str = "dict"

    def __post_init__(self) -> None:
        self._records = _records_to_dicts(self.records)
        if self.graph is None and self.transition_fn is None:
            raise TypeError("AgenticEnvironment requires either graph=... or transition_fn=...")
        graph_source = self.graph if self.graph is not None else _TransitionFunctionGraph(self.transition_fn, self)
        self._graph = _compile_graph(graph_source)
        self._default_episode_id = self.episode_id
        self.episode_id = ""
        self._cursor = 0
        self._steps = 0
        self._done = False
        self._closed = False
        self._memory = self.initial_memory
        self._history: list[EnvironmentTransition] = []

    @property
    def memory(self) -> Any:
        return self._memory

    @property
    def history(self) -> tuple[EnvironmentTransition, ...]:
        return tuple(self._history)

    @property
    def current_step(self) -> int:
        return self._steps

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
        """Start a new episode and return ``(observation, info)``."""

        if self._closed:
            raise RuntimeError("Environment is closed. Create a new AgenticEnvironment to run another episode.")
        self.episode_id = str((options or {}).get("episode_id") or self._default_episode_id or (f"episode-{seed}" if seed is not None else uuid4()))
        self._cursor = int((options or {}).get("start_index", 0))
        if self._cursor < 0 or self._cursor > len(self._records):
            raise ValueError(f"start_index must be between 0 and {len(self._records)}")
        self._steps = 0
        self._done = self._cursor >= len(self._records)
        self._memory = (options or {}).get("memory", self.initial_memory)
        self._history = []
        observation = None if self._done else self._observe(self._records[self._cursor])
        return observation, self._info(event=None, graph_state=None)

    def step(self, action: Any = None) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        """Execute one sync graph transition and return Gymnasium's step tuple."""

        row, state = self._prepare_step(action)
        graph_state = self._invoke_graph(state)
        return self._complete_step(row, action, graph_state)

    async def astep(self, action: Any = None) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        """Execute one async graph transition and return Gymnasium's step tuple."""

        row, state = self._prepare_step(action)
        graph_state = await self._ainvoke_graph(state)
        return self._complete_step(row, action, graph_state)

    def render(self) -> Any:
        """Return a compact episode view."""

        data = {
            "name": self.name,
            "episode_id": self.episode_id,
            "step": self._steps,
            "total_records": len(self._records),
            "done": self._done,
            "memory": self._memory,
            "history": [event.to_dict() for event in self._history],
        }
        if self.render_mode == "ansi":
            return f"{self.name} episode={self.episode_id} step={self._steps}/{len(self._records)} done={self._done}"
        if self.render_mode == "history":
            return data["history"]
        return data


    def summary(self) -> dict[str, Any]:
        """Return a compact, framework-agnostic episode summary."""

        total_reward = sum(float(event.reward or 0.0) for event in self._history)
        passed = sum(1 for event in self._history if float(event.reward or 0.0) > 0.0)
        routes = Counter(_transition_route(event) for event in self._history)
        return {
            "name": self.name,
            "episode_id": self.episode_id,
            "steps": len(self._history),
            "total_records": len(self._records),
            "done": self._done,
            "total_reward": total_reward,
            "passed_steps": passed,
            "failed_steps": len(self._history) - passed,
            "routes": dict(routes),
            "memory": self._memory,
        }

    def normalized(self) -> dict[str, Any]:
        """Return a RunResult-shaped view for ``lab.human_result``.

        Environments are episodes, not model calls.  This method intentionally
        exposes the episode as a human-renderable result while preserving the
        framework-agnostic boundary: no LangGraph/OpenAI/Gymnasium internals are
        required to explain what happened.
        """

        summary = self.summary()
        answer = (
            f"Environment processed {summary['steps']} step(s); "
            f"passed={summary['passed_steps']}, failed={summary['failed_steps']}, "
            f"total_reward={summary['total_reward']}."
        )
        return {
            "schema_version": "agentic_systems.run.v1",
            "ok": bool(summary["failed_steps"] == 0 if summary["steps"] else True),
            "runtime": {
                "engine": "environment",
                "framework": "agentic-environment",
                "mode": "episode",
            },
            "input": {"environment": self.name, "records": summary["total_records"]},
            "answer": {
                "text": answer,
                "final": {"summary": answer, **summary},
                "data": {"summary": summary, "history": [event.to_dict() for event in self._history]},
            },
            "tools": [],
            "usage": {},
            "validation": {
                "ok": bool(summary["failed_steps"] == 0 if summary["steps"] else True),
                "passed_steps": summary["passed_steps"],
                "failed_steps": summary["failed_steps"],
            },
            "errors": [
                {"code": "environment_step_failed", "message": f"step_{event.step_index}"}
                for event in self._history
                if float(event.reward or 0.0) <= 0.0
            ],
        }

    def lineage(
        self,
        *,
        name: str | None = None,
        question: str = "",
        goal: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        max_steps: int | None = None,
    ):
        """Build ``LineageMemory`` from the environment episode history.

        The projection is intentionally independent of the actor behind the
        transition. A row can be processed by a direct tool, one agent, a
        LangGraph app, an OpenAI Agents adapter, or a multi-agent system; the
        environment only records what happened at the step boundary.
        """

        return environment_lineage(
            self,
            name=name,
            question=question,
            goal=goal,
            tags=tags,
            metadata=metadata,
            max_steps=max_steps,
        )

    def close(self) -> None:
        """Mark the environment closed."""

        self._closed = True


    def _prepare_step(self, action: Any) -> tuple[dict[str, Any], GraphState]:
        if self._closed:
            raise RuntimeError("Environment is closed. Create a new AgenticEnvironment to continue.")
        if not self.episode_id:
            raise RuntimeError("Call env.reset(...) before env.step(...).")
        if self._done:
            raise RuntimeError("Episode is done. Call env.reset(...) before stepping again.")

        row = self._records[self._cursor]
        state = self._build_state(row, action)
        return row, state

    def _complete_step(
        self,
        row: dict[str, Any],
        action: Any,
        graph_state: GraphState,
    ) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        reward = self._reward(graph_state, row, action)
        self._memory = self._update_memory(graph_state, row, action)

        self._cursor += 1
        self._steps += 1
        terminated = self._cursor >= len(self._records)
        truncated = bool(self.max_steps is not None and self._steps >= self.max_steps and not terminated)
        self._done = terminated or truncated

        event = EnvironmentTransition(
            episode_id=self.episode_id,
            step_index=self._steps - 1,
            row=row,
            action=action,
            graph_state=graph_state,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            memory=self._memory,
        )
        if self.keep_history:
            self._history.append(event)

        observation = None if self._done else self._observe(self._records[self._cursor])
        return observation, reward, terminated, truncated, self._info(event=event, graph_state=graph_state)

    def _build_state(self, row: dict[str, Any], action: Any) -> GraphState:
        if self.state_factory is not None:
            state = self.state_factory(row, action, self)
            if not isinstance(state, dict):
                raise TypeError("state_factory must return a dict LangGraph state.")
            return state
        return {
            self.row_key: row,
            self.action_key: action,
            self.memory_key: self._memory,
            self.episode_key: {
                "id": self.episode_id,
                "step_index": self._steps,
                "row_index": self._cursor,
                "total_records": len(self._records),
            },
        }

    def _invoke_graph(self, state: GraphState) -> GraphState:
        if not hasattr(self._graph, "invoke"):
            raise TypeError("graph must expose invoke(state) or compile() to a LangGraph app.")
        result = self._graph.invoke(state)
        return result if isinstance(result, dict) else {"output": result}

    async def _ainvoke_graph(self, state: GraphState) -> GraphState:
        if hasattr(self._graph, "ainvoke"):
            result = await self._graph.ainvoke(state)
        elif hasattr(self._graph, "invoke"):
            result = await asyncio.to_thread(self._graph.invoke, state)
        else:
            raise TypeError("graph must expose invoke(state), ainvoke(state) or compile() to a LangGraph app.")
        return result if isinstance(result, dict) else {"output": result}

    def _reward(self, graph_state: GraphState, row: dict[str, Any], action: Any) -> float:
        if self.reward_fn is None:
            return 0.0
        return float(_call_with_supported_args(self.reward_fn, graph_state, row, action, self))

    def _update_memory(self, graph_state: GraphState, row: dict[str, Any], action: Any) -> Any:
        if self.memory_updater is not None:
            return self.memory_updater(self._memory, graph_state, row, action, self)
        return graph_state.get(self.memory_key, self._memory)

    def _observe(self, row: dict[str, Any]) -> Any:
        if self.observation_mapper is None:
            return row
        return self.observation_mapper(row, self)

    def _info(self, *, event: EnvironmentTransition | None, graph_state: GraphState | None) -> dict[str, Any]:
        return {
            "name": self.name,
            "episode_id": self.episode_id,
            "step": self._steps,
            "cursor": self._cursor,
            "total_records": len(self._records),
            "done": self._done,
            "memory": self._memory,
            "transition": None if event is None else event.to_dict(),
            "graph_state": graph_state,
            "history_size": len(self._history),
        }


def environment_lineage(
    environment: AgenticEnvironment,
    *,
    name: str | None = None,
    question: str = "",
    goal: str = "",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    max_steps: int | None = None,
):
    """Project an ``AgenticEnvironment`` episode into ``LineageMemory``.

    This is the common explanation layer for environment/eval notebooks.  It
    does not inspect concrete framework internals; it only uses recorded
    transitions, rewards, routes and step evidence.
    """

    from .lineage import LINEAGE_SCHEMA_VERSION, LineageMemory, LineageStep, _safe_json, _short

    history = list(environment.history)
    selected_history = history if max_steps is None else history[:max_steps]
    summary = environment.summary()
    answer = (
        f"Episode {summary['episode_id']} processed {summary['steps']} step(s); "
        f"passed={summary['passed_steps']}, failed={summary['failed_steps']}, "
        f"total_reward={summary['total_reward']}."
    )
    steps: list[LineageStep] = [
        LineageStep(
            step_id="episode",
            kind="input",
            title="Environment episode",
            summary=_short(question or environment.name, max_chars=320) or f"Episode for {environment.name}.",
            source="AgenticEnvironment",
            why="El environment controla el episodio, no el agente ni el framework externo.",
            evidence={"summary": summary},
        )
    ]

    for event in selected_history:
        route = _transition_route(event)
        output = _transition_output(event.graph_state)
        reward_label = "passed" if float(event.reward or 0.0) > 0.0 else "needs_review"
        summary_text = f"step={event.step_index}; route={route}; reward={event.reward}; status={reward_label}."
        if output:
            summary_text = f"{summary_text} output={_short(output, max_chars=220)}"
        steps.append(
            LineageStep(
                step_id=f"step_{event.step_index}",
                kind="decision" if route not in {"unknown", "tool"} else "context",
                title=f"Environment step {event.step_index}",
                summary=_short(summary_text, max_chars=420),
                source="AgenticEnvironment.history",
                why="Cada step conserva la decisión/ruta, la recompensa y la evidencia mínima del resultado.",
                evidence={
                    "row": event.row,
                    "action": event.action,
                    "route": route,
                    "reward": event.reward,
                    "terminated": event.terminated,
                    "truncated": event.truncated,
                    "output": output,
                    "graph_state_keys": sorted(event.graph_state.keys()),
                },
            )
        )

    steps.append(
        LineageStep(
            step_id="episode_result",
            kind="validation",
            title="Environment scoring",
            summary=answer,
            source="AgenticEnvironment.reward_fn",
            why="El score se calcula paso a paso y queda separado de la ejecución del agente/sistema.",
            evidence={"summary": summary},
        )
    )
    return LineageMemory(
        schema_version=LINEAGE_SCHEMA_VERSION,
        name=name or f"{environment.name}.lineage",
        question=question,
        goal=goal,
        answer=answer,
        ok=summary["failed_steps"] == 0 if summary["steps"] else True,
        steps=steps,
        tags=["environment", *(tags or [])],
        metadata={"environment": summary, **(metadata or {})},
    )


def _transition_route(event: EnvironmentTransition) -> str:
    state = event.graph_state or {}
    row = event.row or {}
    candidates = (
        state.get("selected_agent"),
        state.get("selected_tool"),
        state.get("route"),
        state.get("tool"),
        row.get("agent"),
        row.get("tool"),
        row.get("route"),
    )
    for candidate in candidates:
        if candidate not in (None, "", [], {}):
            return str(candidate)
    return "unknown"


def _transition_output(state: GraphState) -> str:
    for key in ("summary", "answer", "agent_text", "final_answer", "text", "output"):
        value = state.get(key)
        if value not in (None, "", [], {}):
            return str(value)
    result = state.get("result") or state.get("agent_result") or state.get("tool_result")
    if isinstance(result, Mapping):
        for key in ("summary", "text", "answer"):
            value = result.get(key)
            if value not in (None, "", [], {}):
                return str(value)
        return str({key: result.get(key) for key in ("ok", "tool", "route", "rows") if key in result})
    return ""



class _TransitionFunctionGraph:
    """Adapter that lets simple row/action transition functions act as graphs."""

    def __init__(self, transition_fn: TransitionFn | None, env: AgenticEnvironment) -> None:
        if transition_fn is None:
            raise TypeError("transition_fn must be provided when graph is omitted.")
        self.transition_fn = transition_fn
        self.env = env

    def invoke(self, state: GraphState) -> GraphState:
        row = state.get(self.env.row_key, {})
        action = state.get(self.env.action_key)
        info = {
            "episode": state.get(self.env.episode_key, {}),
            "memory": state.get(self.env.memory_key),
            "state": state,
        }
        result = self.transition_fn(row, action, info)
        if not isinstance(result, dict):
            raise TypeError("transition_fn must return a dict graph state.")
        return {**state, **result}


def _call_with_supported_args(fn: Callable[..., Any], *args: Any) -> Any:
    """Call fn with as many positional args as its signature accepts.

    This keeps notebooks ergonomic: reward functions may be ``fn(state)`` for
    simple demos or ``fn(state, row, action, env)`` for full-control runs.
    """

    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):  # pragma: no cover - unusual callables
        return fn(*args)
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
    ]
    has_varargs = any(parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in signature.parameters.values())
    if has_varargs:
        return fn(*args)
    return fn(*args[: len(positional)])




def _read_graph_input(state: GraphState, input: str | Callable[[GraphState], Any]) -> Any:
    if callable(input):
        return input(state)
    if input not in state:
        raise KeyError(f"Input key {input!r} not found in graph state. Available: {sorted(state)}")
    return state[input]


def _map_agent_result(
    result: Any,
    state: GraphState,
    output: str | Callable[[Any, GraphState], Mapping[str, Any]] | None,
    trace: str | None,
    result_key: str | None,
) -> dict[str, Any]:
    update: dict[str, Any] = {}
    if callable(output):
        mapped = output(result, state)
        if not isinstance(mapped, Mapping):
            raise TypeError("Custom output mapper must return a mapping.")
        update.update(dict(mapped))
    elif output is not None:
        update[output] = getattr(result, "text", result)
    if result_key is not None:
        update[result_key] = result.to_dict() if hasattr(result, "to_dict") else result
    if trace is not None:
        update[trace] = result.trace("compact") if hasattr(result, "trace") else result
    return update


def build_single_agent_step_graph(
    agent: Any,
    *,
    input: str | Callable[[GraphState], Any] = "row",
    output: str | Callable[[Any, GraphState], Any] | None = "agent_text",
    trace: str | None = "agent_trace",
    node_name: str = "agent_step",
    state: Any = dict,
    async_node: bool = False,
    **node_kwargs: Any,
) -> Any:
    """Build and compile a one-node LangGraph step app for an agent.

    The returned object is a native compiled LangGraph app. It can be passed to
    ``AgenticEnvironment(graph=...)``.
    """

    try:
        from langgraph.graph import END, START, StateGraph
    except Exception as exc:  # pragma: no cover - exercised only when optional dependency is absent
        raise ImportError("build_single_agent_step_graph requires langgraph. Install with: pip install -e '.[langgraph]'") from exc

    graph = StateGraph(state)
    node_factory = agent.as_async_node if async_node else agent.as_node
    graph.add_node(node_name, node_factory(input=input, output=output, trace=trace, **node_kwargs))
    graph.add_edge(START, node_name)
    graph.add_edge(node_name, END)
    return graph.compile()


def _compile_graph(graph: Any) -> Any:
    if hasattr(graph, "invoke"):
        return graph
    if hasattr(graph, "compile"):
        return graph.compile()
    return graph


def _records_to_dicts(records: Any) -> list[dict[str, Any]]:
    if hasattr(records, "to_dict"):
        converted = records.to_dict(orient="records")
        return [dict(item) for item in converted]
    if isinstance(records, Mapping):
        return [dict(records)]
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes)):
        return [dict(item) for item in records]
    raise TypeError("records must be a pandas DataFrame, mapping or iterable of mappings.")


__all__ = [
    "AgenticEnvironment",
    "EnvironmentTransition",
    "AgentStepGraph",
    "DynamicAgentRouterGraph",
    "PlannedAgentGraph",
    "build_agent_step_graph",
    "build_dynamic_agent_router_graph",
    "build_planned_agent_graph",
    "build_single_agent_step_graph",
    "environment_lineage",
]
