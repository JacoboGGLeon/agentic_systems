"""Private implementation of the single Agentic Systems 2.1.3 API."""

from __future__ import annotations

import asyncio
import json
import operator
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, TypedDict

from ._actors import Agent as _Actor
from .tools import Tool as _Tool
from .skills.skill import Skill as _Skill
from .results import RunResult as _RunResult
from .contracts import ValidationResult as _ValidationResult
from .core.runtime import RuntimeConfig as _RuntimeConfig
from .integrations.config import FrameworkConfig as _FrameworkConfig
from ._factories import agent as _make_actor, environment as _environment, eval as _evaluator


def snapshot(value):
    def check(item):
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise TypeError("JSON state requires string keys")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif type(item) not in {str, int, float, bool, type(None)}:
            raise TypeError("Business state must contain only JSON values")

    check(value)
    return json.loads(json.dumps(value, allow_nan=False))


def identity(value):
    return value


@dataclass(frozen=True)
class Action:
    name: str
    target: Any  # callable, public Tool, python-runtime Agent, or Skill Tool name
    input: Callable = identity


@dataclass(frozen=True)
class Sequence:
    steps: tuple
    name: str = "sequence"


@dataclass(frozen=True)
class Parallel:
    steps: tuple
    join: Callable
    name: str = "parallel"


@dataclass(frozen=True)
class Graph:
    nodes: tuple  # (name, flow) pairs; a Parallel node expresses explicit fork/join
    edges: tuple  # (source, destination name | callable | legacy decision function) pairs
    start: str
    max_visits: int = 20
    name: str = "graph"


@dataclass(frozen=True)
class Limits:
    max_actions: int = 100
    timeout_s: float = 10


class Context:
    def __init__(self, limits):
        if limits.max_actions < 1 or limits.timeout_s <= 0:
            raise ValueError("Limits must be positive")
        self.limits = limits
        self.started = time.monotonic()
        self.actions = 0
        self.lock = threading.Lock()

    def check(self):
        if time.monotonic() - self.started >= self.limits.timeout_s:
            raise TimeoutError("Shared run deadline exceeded")

    def take(self):
        with self.lock:
            self.check()
            if self.actions >= self.limits.max_actions:
                raise RuntimeError("Shared action limit exceeded")
            self.actions += 1


def result(name, kind, data, children=(), error=None, **meta):
    children = list(children)
    execution_id = "run-" + uuid.uuid4().hex
    for child in children:
        child.parent_execution_id = execution_id
    errors = [{"code": type(error).__name__, "message": str(error)}] if error else []
    return _RunResult(
        data=snapshot(data),
        ok=error is None and all(child.ok for child in children),
        errors=errors,
        children=children,
        engine="python-runtime",
        execution_id=execution_id,
        meta={"name": name, "kind": kind, **meta},
    )


class _State(TypedDict, total=False):
    value: Any
    context: Context
    records: Annotated[list, operator.add]
    failed: bool
    next: str
    visits: int


@dataclass(frozen=True)
class _Prepared:
    name: str
    kind: str
    backend: str
    execute: Callable
    native: Any = None
    children: tuple = ()

    def run(self, value, context):
        try:
            return self.execute(snapshot(value), context)
        except Exception as exc:
            return result(self.name, self.kind, {}, error=exc, backend=self.backend)


def _action(action, registry, reserve=True):
    target = (
        registry[action.target] if isinstance(action.target, str) else action.target
    )
    if not callable(action.input):
        raise TypeError("Action input binding must be callable")
    if not isinstance(target, (_Actor, _Tool)) and not callable(target):
        raise TypeError("Action target must be a Tool, Python Agent or callable")

    def execute(value, context):
        children = []
        try:
            context.take() if reserve else context.check()
            payload = snapshot(action.input(value))
            raw = (
                target.run(payload)
                if isinstance(target, (_Tool, _Actor))
                else target(payload)
            )
            if isinstance(raw, _RunResult):
                # SDK-private native objects can be cyclic. Copy the result shell
                # to attach its parent without deep-copying framework internals.
                raw = raw.model_copy()
                raw.execution_id = raw.execution_id or "leaf-" + uuid.uuid4().hex
                children.append(raw)
                data = raw.data
            else:
                data = raw
            data = snapshot(data)
            context.check()  # preserve a Tool result even if it completed late
            return result(action.name, "action", data, children)
        except Exception as exc:
            return result(
                action.name,
                "action",
                children[-1].data if children else {},
                children,
                exc,
            )

    return _Prepared(action.name, "action", "python", execute)


def _composite(flow, backend, children):
    names = [child.name for child in children]
    if (
        len(set(names)) != len(names)
        or not names
        or any(not name or name == "END" or name.startswith("__") for name in names)
    ):
        raise ValueError("Flow requires unique nonempty step names other than END")
    kind = type(flow).__name__.lower()
    graph_nodes = dict(zip(names, children))
    edges = dict(flow.edges) if isinstance(flow, Graph) else {}
    if isinstance(flow, Graph):
        if (
            len(edges) != len(flow.edges)
            or set(edges) != set(names)
            or flow.start not in names
        ):
            raise ValueError(
                "Graph requires a start and exactly one edge/decision function per node"
            )
        if flow.max_visits < 1:
            raise ValueError("Graph visit limit must be positive")
        for edge in edges.values():
            if callable(edge):
                # Direct routers may select any node in this graph or END.
                # Never execute or inspect user code to infer its destinations.
                continue
            if not isinstance(edge, str):
                raise TypeError("Graph edge must be a destination name or callable")
            targets = (edge,)
            if not targets or any(target not in {*names, "END"} for target in targets):
                raise ValueError("Unknown graph target")
    if isinstance(flow, Parallel) and not callable(flow.join):
        raise TypeError("Parallel requires an explicit join")

    def node(name, state):
        context = state["context"]
        visits = state.get("visits", 0) + 1
        if isinstance(flow, Graph) and visits > flow.max_visits:
            current = result(
                name,
                "visit-limit",
                {},
                error=RuntimeError("Graph visit limit exceeded"),
            )
        else:
            current = graph_nodes[name].run(state["value"], context)
        current.meta["graph_node" if isinstance(flow, Graph) else "step"] = name
        records = [(name, current)]
        update = {
            "value": current.data,
            "records": records,
            "failed": not current.ok,
            "visits": visits,
        }
        if isinstance(flow, Graph) and current.ok:
            try:
                edge = edges[name]
                router = edge if callable(edge) else None
                if router is not None:
                    context.take()
                    target = router(snapshot(current.data))
                    context.check()
                    targets = (*names, "END")
                    if not isinstance(target, str) or target not in targets:
                        raise ValueError("decision functionr selected an undeclared target")
                else:
                    target = edge
                current.meta["next"] = target
                update["next"] = target
            except Exception as exc:
                records.append(
                    (name + ":route", result(name + ":route", "route", {}, error=exc))
                )
                update["failed"] = True
        return update

    def join(records):
        ordered = [dict(records)[name] for name in names]
        try:
            data = (
                flow.join(
                    {name: snapshot(child.data) for name, child in zip(names, ordered)}
                )
                if all(c.ok for c in ordered)
                else {"branches": {name: c.data for name, c in zip(names, ordered)}}
            )
            return result(flow.name, kind, data, ordered, backend=backend)
        except Exception as exc:
            return result(flow.name, kind, {}, ordered, exc, backend=backend)

    native = None
    if backend == "langgraph":
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(_State)
        if isinstance(flow, Parallel):
            for name in names:

                def branch(state, name=name):
                    return {
                        "records": [
                            (
                                name,
                                graph_nodes[name].run(state["value"], state["context"]),
                            )
                        ]
                    }

                builder.add_node(name, branch)
                builder.add_edge(START, name)
            # A real barrier: join waits for every branch; never multiple writes to value.
            builder.add_node("__join__", lambda state: {})
            builder.add_edge(names, "__join__")
            builder.add_edge("__join__", END)
        else:
            for index, name in enumerate(names):
                builder.add_node(name, lambda state, name=name: node(name, state))
                if isinstance(flow, Graph):
                    builder.add_conditional_edges(
                        name,
                        lambda state: "END" if state["failed"] else state["next"],
                        {n: n for n in names} | {"END": END},
                    )
                else:
                    following = names[index + 1] if index + 1 < len(names) else "END"
                    builder.add_conditional_edges(
                        name,
                        lambda state, following=following: (
                            "END" if state["failed"] else following
                        ),
                        {n: n for n in names} | {"END": END},
                    )
            builder.add_edge(START, flow.start if isinstance(flow, Graph) else names[0])
        native = builder.compile()

    def execute(value, context):
        state = {
            "value": value,
            "context": context,
            "records": [],
            "failed": False,
            "visits": 0,
        }
        if native is not None:
            state = native.invoke(
                state,
                config={
                    "recursion_limit": (
                        flow.max_visits if isinstance(flow, Graph) else len(names)
                    )
                    + 10
                },
            )
        elif isinstance(flow, Parallel):
            with ThreadPoolExecutor(max_workers=min(len(names), 8)) as pool:
                outputs = list(
                    pool.map(lambda c: c.run(snapshot(value), context), children)
                )
            state["records"] = list(zip(names, outputs))
        else:
            current = flow.start if isinstance(flow, Graph) else names[0]
            while current != "END":
                update = node(current, state)
                state = {
                    **state,
                    **update,
                    "records": state["records"] + update["records"],
                }
                if state["failed"]:
                    break
                current = (
                    state["next"]
                    if isinstance(flow, Graph)
                    else (
                        names[names.index(current) + 1]
                        if names.index(current) + 1 < len(names)
                        else "END"
                    )
                )
        if isinstance(flow, Parallel):
            output = join(state["records"])
            try:
                context.check()
            except TimeoutError as exc:
                output.ok = False
                output.errors.append({"code": "TimeoutError", "message": str(exc)})
            return output
        return result(
            flow.name,
            kind,
            state["value"],
            [r for _, r in state["records"]],
            backend=backend,
        )

    return _Prepared(flow.name, kind, backend, execute, native, tuple(children))


def _prepare(flow, backend, registry, seen):
    if id(flow) in seen:
        raise ValueError("Recursive owner/flow definition")
    seen = {*seen, id(flow)}
    if isinstance(flow, Unit):
        return flow._compile(seen)
    if isinstance(flow, Action):
        return _action(flow, registry)
    if isinstance(flow, (Sequence, Parallel)):
        if not isinstance(flow.steps, tuple):
            raise TypeError("Flow steps must be an immutable tuple")
        return _composite(
            flow,
            backend,
            tuple(_prepare(step, backend, registry, seen) for step in flow.steps),
        )
    if isinstance(flow, Graph):
        if not isinstance(flow.nodes, tuple) or not isinstance(flow.edges, tuple):
            raise TypeError("Graph nodes and edges must be immutable tuples")
        keys = [name for name, _ in flow.nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate graph node")
        children = []
        for name, step in flow.nodes:
            compiled = _prepare(step, backend, registry, seen)
            # Graph node key is explicit; nested owner metadata is preserved inside.
            children.append(
                _Prepared(
                    name,
                    compiled.kind,
                    compiled.backend,
                    compiled.run,
                    compiled.native,
                    compiled.children,
                )
            )
        return _composite(flow, backend, tuple(children))
    raise TypeError("Expected Action, Sequence, Parallel, Graph, Agent or System")


@dataclass(frozen=True)
class Unit:
    name: str
    flow: Any = None
    backend: str = "native"
    skills: tuple = ()
    kind: str = field(default="unit", init=False)

    def _compile(self, seen):
        if self.backend not in {"native", "langgraph"}:
            raise ValueError("Unsupported flow backend; no auto fallback")
        if not isinstance(self.skills, tuple):
            raise TypeError("Skills must be an immutable tuple")
        registry = {}
        for skill in self.skills:
            if not isinstance(skill, _Skill):
                raise TypeError("Expected a real Agentic Systems Skill")
            for tool in skill.tools:
                if tool.name in registry and registry[tool.name] is not tool:
                    raise ValueError("Conflicting Skill Tool identity")
                registry[tool.name] = tool
        if isinstance(self, Agent) and self.runtime is not None:
            body = _model_body(self)
        else:
            if self.flow is None:
                raise ValueError("A flow is required")
            body = _prepare(self.flow, self.backend, registry, seen)
        skill_names = [skill.name for skill in self.skills]

        def execute(value, context):
            child = body.run(value, context)
            output = result(
                self.name,
                self.kind,
                child.data,
                [child],
                backend=self.backend,
                skills=skill_names,
            )
            output.engine = child.engine
            return output

        return _Prepared(self.name, self.kind, self.backend, execute, children=(body,))

    def compile(self):
        if not self.name:
            raise ValueError("Owner name is required")
        return Compiled(self._compile({id(self)}))

    def run(self, input=None, *, limits=Limits()):
        return self.compile().run(input, limits=limits)

    async def arun(self, input=None, *, limits=Limits()):
        return await self.compile().arun(input, limits=limits)

    def inspect(self):
        return self.compile().inspect()


@dataclass(frozen=True)
class Agent(Unit):
    runtime: Any = None
    framework: Any = None
    instructions: str = ""
    contract: dict | None = None
    policy: dict | None = None
    kind: str = field(default="agent", init=False)

    def __post_init__(self):
        if (self.flow is None) == (self.runtime is None):
            raise ValueError("Agent needs a flow or an explicit runtime")
        if self.runtime is None and (self.framework is not None or self.instructions or self.contract or self.policy):
            raise ValueError("Model options belong to an Agent with an explicit runtime")


@dataclass(frozen=True)
class System(Unit):
    kind: str = field(default="system", init=False)


@dataclass(frozen=True)
class Compiled:
    prepared: _Prepared

    def run(self, input=None, *, limits=Limits()):
        context = Context(limits)
        output = self.prepared.run(input, context)
        output.meta["actions_observed"] = context.actions
        return output

    async def arun(self, input=None, *, limits=Limits()):
        return await asyncio.to_thread(self.run, input, limits=limits)

    def inspect(self):
        def describe(node):
            return {
                "name": node.name,
                "kind": node.kind,
                "backend": node.backend,
                "native_type": type(node.native).__name__ if node.native else None,
                "children": [describe(child) for child in node.children],
            }

        return describe(self.prepared)


@dataclass(frozen=True)
class Environment:
    name: str
    unit: Unit
    records: tuple
    max_steps: int | None = None

    def compile(self):
        if not self.records or (self.max_steps is not None and self.max_steps < 1):
            raise ValueError("Environment needs records and a positive step limit")
        return _CompiledEnvironment(
            self.name,
            self.unit.compile(),
            json.dumps(snapshot(list(self.records))),
            self.max_steps,
        )

    def run(self, *, limits=Limits()):
        return self.compile().run(limits=limits)


@dataclass(frozen=True)
class _CompiledEnvironment:
    name: str
    unit: Compiled
    records_json: str
    max_steps: int | None

    def run(self, *, limits=Limits()):
        context = Context(limits)
        children = []

        class Transition:
            def invoke(self, state):
                child = self_unit.prepared.run(state["row"], context)
                children.append(child)
                return {
                    **state,
                    "run": child.to_dict(),
                    "memory": {
                        "processed": state.get("memory", {}).get("processed", 0) + 1
                    },
                }

        self_unit = self.unit
        session = _environment(
            json.loads(self.records_json),
            graph=Transition(),
            name=self.name,
            max_steps=self.max_steps,
            reward_fn=lambda state, *_: 1.0 if state["run"]["ok"] else -1.0,
        )
        observation, _ = session.reset(
            options={"episode_id": "episode-" + uuid.uuid4().hex}
        )
        while observation is not None:
            observation, _, terminated, truncated, _ = session.step()
            if terminated or truncated:
                break
        data = {
            "summary": session.summary(),
            "history": [step.to_dict() for step in session.history],
            "outputs": [child.data for child in children],
        }
        session.close()
        incomplete = len(children) < len(json.loads(self.records_json))
        return result(
            self.name,
            "environment",
            data,
            children,
            error=RuntimeError("Episode truncated before all records")
            if incomplete
            else None,
            actions_observed=context.actions,
        )


@dataclass(frozen=True)
class Eval:
    name: str
    unit: Unit
    cases: tuple

    def compile(self):
        if not self.cases:
            raise ValueError("Eval requires cases")
        for case in self.cases:
            if set(case.get("expected", {})) - {"ok", "data"}:
                raise ValueError("Prototype Eval supports only exact expected ok/data")
        return _CompiledEval(
            self.name, self.unit.compile(), json.dumps(snapshot(list(self.cases)))
        )

    def run(self, *, limits=Limits()):
        return self.compile().run(limits=limits)


@dataclass(frozen=True)
class _CompiledEval:
    name: str
    unit: Compiled
    cases_json: str

    def run(self, *, limits=Limits()):
        # The existing deterministic Eval checks the expected contract. No judge.
        context = Context(limits)
        prepared = self.unit.prepared

        class Target:
            def run(self, input=None, **kwargs):
                return prepared.run(input, context)

        def exact_expected(output, case):
            validation = _ValidationResult()
            for key, expected in case.get("expected", {}).items():
                actual = output.data if key == "data" else output.ok
                if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(
                    expected, sort_keys=True, allow_nan=False
                ):
                    validation.add(
                        "expected_mismatch",
                        f"Exact {key} does not match",
                        path=key,
                    )
            return validation

        report = _evaluator().evaluate(
            Target(),
            json.loads(self.cases_json),
            determinism="deterministic",
            assertions=(exact_expected,),
        )
        children = [
            _RunResult.model_validate(case.result) for case in report.cases
        ]
        output = result(self.name, "eval", report.to_dict(), children)
        output.ok = output.ok and report.ok
        output.meta["actions_observed"] = context.actions
        if not report.ok:
            output.errors.append(
                {"code": "eval_failed", "message": report.summary_text()}
            )
        return output


def _model_body(owner):
    """Prepare configuration; instantiate the provider only when run is called."""
    if not isinstance(owner.runtime, _RuntimeConfig):
        raise TypeError("Use runtime(...) for a model Agent")
    selected_framework = _FrameworkConfig.coerce(owner.framework)

    def execute(value, context):
        context.take()
        raw = _make_actor(name=owner.name, instructions=owner.instructions,
                          skills=owner.skills, runtime=owner.runtime,
                          framework=selected_framework, contract=owner.contract,
                          policy=owner.policy)
        output = _action(Action(owner.name, raw), {}, reserve=False).run(value, context)
        output.engine = raw.engine
        return output

    return _Prepared(owner.name, "model", selected_framework.name, execute)
