"""Private implementation of the single Agentic Systems 2.1.3 API."""

from __future__ import annotations

import asyncio
import json
import operator
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from typing import Annotated, Any, Callable, TypedDict

from ._tools import _Tool, _Skill
from ._results import RunResult as _RunResult
from ._configuration import _Runtime, _Framework, framework
from ._contracts import _validate_contract, _validate_policy, _invoke_actor, _check_output, _closed



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

    def __post_init__(self):
        import math
        if type(self.max_actions) is not int or self.max_actions < 1:
            raise ValueError("max_actions must be a positive integer")
        if type(self.timeout_s) not in {int, float} or not math.isfinite(self.timeout_s) or self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive and finite")


class Context:
    def __init__(self, limits):
        if not isinstance(limits, Limits):
            raise TypeError("Use Limits(...)")
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
    execution_id = "run-" + uuid.uuid4().hex
    children = tuple(replace(c, parent_execution_id=execution_id) for c in children)
    errors = ([{"code": type(error).__name__, "message": str(error)}] if error else [])
    for child in children:
        errors.extend(child.errors)
    allowed_ids = {identity for child in children for identity in child.meta.get("allowed_error_ids", ())}
    if errors and error is None and all(not c.errors or c.execution_id in allowed_ids for c in children):
        allowed_ids.add(execution_id)
    if allowed_ids:
        meta["allowed_error_ids"] = sorted(allowed_ids)
    usage = {}
    for child in children:
        for key, value in child.usage.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    return _RunResult(data=snapshot(data),
        text=children[-1].text if children and kind != "parallel" else "",
        final=children[-1].final if children and kind != "parallel" else None,
        ok=error is None and all(c.ok for c in children),
        errors=tuple(errors), children=children, usage=usage, engine="python-runtime",
        execution_id=execution_id, meta={"name": name, "kind": kind, **meta})


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
    if not isinstance(target, _Tool) and not callable(target):
        raise TypeError("Action target must be a Tool or callable")

    def execute(value, context):
        children = []
        try:
            context.take() if reserve else context.check()
            payload = snapshot(action.input(value))
            raw = (
                target.run(payload)
                if isinstance(target, _Tool)
                else target(payload)
            )
            if isinstance(raw, _RunResult):
                # SDK-private native objects can be cyclic. Copy the result shell
                # to attach its parent without deep-copying framework internals.
                raw = replace(raw)
                
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
        if type(flow.max_visits) is not int or flow.max_visits < 1:
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
                        raise ValueError("decision function selected an undeclared target")
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
                output = replace(output, ok=False, errors=(*output.errors, {"code": "TimeoutError", "message": str(exc)}))
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
    if isinstance(flow, _Unit):
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
class _Unit:
    name: str
    flow: Any = None
    backend: str = "native"
    kind: str = field(default="unit", init=False)

    def _compile(self, seen):
        if self.backend not in {"native", "langgraph"}:
            raise ValueError("Unsupported flow backend; no auto fallback")
        if not isinstance(getattr(self, "skills", ()), tuple):
            raise TypeError("Skills must be an immutable tuple")
        registry = {}
        for skill in getattr(self, "skills", ()):
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
        skill_names = [skill.name for skill in getattr(self, "skills", ())]

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
            return replace(output, engine=child.engine, model=child.model)

        return _Prepared(self.name, self.kind, self.backend, execute, children=(body,))

    def compile(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Owner name is required")
        return _Compiled(self._compile({id(self)}))

    def run(self, input=None, *, limits=Limits()):
        return self.compile().run(input, limits=limits)

    async def arun(self, input=None, *, limits=Limits()):
        return await self.compile().arun(input, limits=limits)

    def inspect(self):
        return self.compile().inspect()


@dataclass(frozen=True)
class Agent(_Unit):
    skills: tuple = ()
    runtime: Any = None
    framework: Any = None
    instructions: str = ""
    contract: dict | None = None
    policy: dict | None = None
    kind: str = field(default="agent", init=False)

    def __post_init__(self):
        if self.runtime is not None and self.backend != "native":
            raise ValueError("backend selects a flow, not the actor framework")
        if (self.flow is None) == (self.runtime is None):
            raise ValueError("Agent needs a flow or an explicit runtime")
        if self.runtime is None and (self.framework is not None or self.instructions or self.contract is not None or self.policy is not None):
            raise ValueError("Model options belong to an Agent with an explicit runtime")


@dataclass(frozen=True)
class System(_Unit):
    kind: str = field(default="system", init=False)


@dataclass(frozen=True)
class _Compiled:
    _prepared: _Prepared

    def run(self, input=None, *, limits=Limits()):
        context = Context(limits)
        output = self._prepared.run(input, context)
        metadata = {**output.meta, "actions_observed": context.actions}
        try:
            metadata["input"] = snapshot(input)
        except (ValueError, TypeError):
            metadata["input_error"] = "Input is not finite JSON"
        output = replace(output, meta=metadata)
        return _boundary(output)

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

        return describe(self._prepared)


def _boundary(output):
    validation = output.check_invariants()
    if not validation.ok:
        return replace(output, ok=False, errors=(*output.errors, {"code": "invariant_failed", "issues": validation.to_dict()["issues"]}))
    return output


def _model_body(owner):
    if not isinstance(owner.runtime, _Runtime):
        raise TypeError("Use runtime(...)")
    if not isinstance(owner.instructions, str):
        raise TypeError("instructions must be a string")
    selected = framework("native") if owner.framework is None else owner.framework
    if not isinstance(selected, _Framework):
        raise TypeError("Use framework(...)")
    if owner.runtime.provider != "python-runtime" and not owner.runtime.model:
        raise ValueError("An external model Agent requires an explicit model identity")
    names = [t.name for s in owner.skills for t in s.tools]
    contract = _validate_contract(owner.contract, names, owner.runtime)
    policy = _validate_policy(owner.policy)
    required = contract.get("tool_expectation", {}).get("all_of", [])
    if required and policy.get("tool_choice") == "none":
        raise ValueError("Required Tools conflict with tool_choice=none")
    if contract.get("completion") == "always_finalize" and policy.get("finalize") == "never":
        raise ValueError("Conflicting completion and finalize rules")

    def execute(value, context):
        context.take()
        child = _invoke_actor(owner, owner.runtime, selected, contract, policy, value)
        child = _check_output(child, contract)
        output = result(owner.name, "model", child.data, (child,), framework=selected.name)
        output = replace(output, engine=child.engine, model=child.model)
        try:
            context.check()
            return output
        except Exception as exc:
            return replace(output, ok=False, errors=(*output.errors, {"code": type(exc).__name__, "message": str(exc)}))

    return _Prepared(owner.name, "model", selected.name, execute)


@dataclass(frozen=True)
class _Captured:
    _name: str
    _kind: str
    _execute: Callable
    _description: dict

    def run(self, *, limits=Limits()):
        context = Context(limits)
        return _boundary(self._execute(context))

    async def arun(self, *, limits=Limits()):
        return await asyncio.to_thread(self.run, limits=limits)

    def inspect(self):
        return snapshot(self._description)


@dataclass(frozen=True)
class Environment:
    name: str
    unit: _Unit
    records: tuple
    max_steps: int | None = None
    memory: Any = None
    observe: Callable | None = None
    update: Callable | None = None
    stop: Callable | None = None

    def compile(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Environment name is required")
        if not isinstance(self.unit, _Unit):
            raise TypeError("Environment runs an Agent or System")
        if not isinstance(self.records, tuple) or not self.records:
            raise ValueError("Environment requires a nonempty tuple of records")
        if self.max_steps is not None and (type(self.max_steps) is not int or self.max_steps < 1):
            raise ValueError("max_steps must be positive")
        if any(fn is not None and not callable(fn) for fn in (self.observe, self.update, self.stop)):
            raise TypeError("Episode callbacks must be functions")
        prepared = self.unit.compile()
        records, initial = snapshot(list(self.records)), snapshot(self.memory)
        description = {"name": self.name, "kind": "environment", "records": len(records),
                       "max_steps": self.max_steps, "memory": initial is not None,
                       "observe": self.observe is not None, "update": self.update is not None,
                       "stop": self.stop is not None, "unit": prepared.inspect()}

        def execute(context):
            memory = snapshot(initial if initial is not None else {})
            children, history, stopped, error = [], [], False, None
            for index, row in enumerate(records):
                if self.max_steps is not None and index >= self.max_steps:
                    error = RuntimeError("Episode truncated before all records")
                    break
                before = snapshot(memory)
                try:
                    context.check()
                    if self.observe is not None:
                        context.take()
                    value = self.observe(snapshot(row), snapshot(memory)) if self.observe else snapshot(row)
                    child = prepared._prepared.run(value, context)
                    children.append(child)
                    if child.ok:
                        if self.update is not None:
                            context.take()
                            memory = snapshot(self.update(snapshot(memory), snapshot(row), _RunResult(**child.to_dict())))
                        elif initial is None:
                            memory = {"processed": len(children)}
                        if self.stop is not None:
                            context.take()
                            stopped = self.stop(snapshot(memory), _RunResult(**child.to_dict()))
                            if type(stopped) is not bool:
                                raise TypeError("stop must return a bool")
                    history.append({"step": index, "record": snapshot(row), "memory_before": before,
                                    "memory_after": snapshot(memory), "graph_state": {"run": child.to_dict()}})
                    context.check()
                    if stopped or not child.ok:
                        break
                except Exception as exc:
                    error = exc
                    if history and history[-1]["step"] == index:
                        history[-1]["error"] = {"code": type(exc).__name__, "message": str(exc)}
                    else:
                        history.append({"step": index, "record": snapshot(row), "memory_before": before,
                                        "memory_after": snapshot(memory), "error": {"code": type(exc).__name__, "message": str(exc)}})
                    break
            data = {"outputs": [c.data for c in children], "history": history,
                    "summary": {"memory": memory, "processed": len(children), "terminated": stopped,
                                "truncated": error is not None and len(children) < len(records)}}
            return result(self.name, "environment", data, children, error, actions_observed=context.actions)

        return _Captured(self.name, "environment", execute, description)

    def run(self, *, limits=Limits()):
        return self.compile().run(limits=limits)

    async def arun(self, *, limits=Limits()):
        return await self.compile().arun(limits=limits)

    def inspect(self):
        return self.compile().inspect()


def _rubric(value):
    rubric = _closed(value, {"criteria", "threshold", "instructions", "certification_tool", "require_failure_findings"}, "rubric")
    criteria = rubric.get("criteria", ["request_fulfillment", "evidence_correctness", "clarity", "no_technical_noise", "no_unsupported_claims"])
    if not isinstance(criteria, list) or not criteria or len(set(criteria)) != len(criteria) or any(not isinstance(c, str) or not c for c in criteria):
        raise ValueError("Rubric criteria require distinct nonempty strings")
    threshold = rubric.get("threshold", 0.8)
    if type(threshold) not in {int, float} or not 0 <= threshold <= 1:
        raise ValueError("threshold must be between zero and one")
    if type(rubric.get("require_failure_findings", True)) is not bool:
        raise TypeError("require_failure_findings must be boolean")
    if not isinstance(rubric.get("instructions", ""), str):
        raise TypeError("Rubric instructions must be a string")
    if rubric.get("certification_tool") is not None and (not isinstance(rubric["certification_tool"], str) or not rubric["certification_tool"]):
        raise TypeError("certification_tool must be a nonempty string")
    return {"criteria": criteria, "threshold": threshold, "instructions": rubric.get("instructions", "Evaluate only against the supplied expected contract and execution evidence."),
            "certification_tool": rubric.get("certification_tool"), "require_failure_findings": rubric.get("require_failure_findings", True)}


def _judge_verdict(judged, actual, rubric):
    raw = _closed(judged.data, {"criteria", "findings", "rationale", "ok", "score"}, "judge output")
    scores = raw.get("criteria", {})
    if not isinstance(scores, dict) or set(scores) != set(rubric["criteria"]):
        raise ValueError("Judge must score every rubric criterion exactly once")
    if any(type(v) not in {int, float} or not 0 <= v <= 1 for v in scores.values()):
        raise ValueError("Judge scores must be numbers between zero and one")
    failed = {k for k, v in scores.items() if v < rubric["threshold"]}
    findings = raw.get("findings", [])
    if not isinstance(findings, list):
        raise TypeError("Judge findings must be a list")
    for item in findings:
        if not isinstance(item, dict) or set(item) != {"criterion", "evidence"} or item["criterion"] not in scores or not isinstance(item["evidence"], str) or not item["evidence"].strip():
            raise ValueError("Each finding requires a scored criterion and evidence")
    if failed and rubric["require_failure_findings"] and not failed <= {f["criterion"] for f in findings}:
        raise ValueError("A failing criterion requires evidence-backed findings")
    certification = rubric["certification_tool"]
    certified = not certification or any(e.name == certification and e.ok for r in actual.walk() for e in r.tool_events)
    score = min(scores.values())
    ok = judged.ok and not failed and certified
    consistent = ("ok" not in raw or type(raw["ok"]) is bool and raw["ok"] == ok) and ("score" not in raw or type(raw["score"]) in {int, float} and raw["score"] == score)
    return {"ok": ok and consistent, "criteria": scores, "score": score, "raw": raw,
            "findings": findings, "consistent": consistent, "certification_recorded": certified,
            "threshold": rubric["threshold"], "usage": judged.usage}


@dataclass(frozen=True)
class Eval:
    name: str
    unit: Any
    cases: tuple
    checks: tuple = ()
    judge: Agent | None = None
    rubric: dict | None = None

    def compile(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Eval name is required")
        if not isinstance(self.unit, (_Unit, Environment)):
            raise TypeError("Eval targets Agent, System or Environment")
        if not isinstance(self.cases, tuple) or not self.cases:
            raise ValueError("Eval requires a nonempty tuple of cases")
        if not isinstance(self.checks, tuple) or any(not callable(c) for c in self.checks):
            raise TypeError("checks must be a tuple of functions")
        if self.judge is not None and not isinstance(self.judge, Agent):
            raise TypeError("judge must be an Agent")
        if self.judge is None and self.rubric is not None:
            raise ValueError("A rubric requires a judge")
        rubric = _rubric(self.rubric) if self.judge else None
        judge = self.judge.compile() if self.judge else None
        cases, targets = snapshot(list(self.cases)), []
        for case in cases:
            _closed(case, {"name", "input", "expected"}, "case")
            expected = _closed(case.get("expected"), {"ok", "data"}, "expected")
            if "ok" in expected and type(expected["ok"]) is not bool:
                raise TypeError("expected.ok must be boolean")
            if "data" in expected and not isinstance(expected["data"], dict):
                raise TypeError("expected.data must be a dictionary")
            if not expected and not self.checks and judge is None:
                raise ValueError("A case needs an expectation, a check or a judge")
            if isinstance(self.unit, Environment):
                value = _closed(case.get("input"), {"records", "memory"}, "episode input")
                episode = replace(self.unit, records=tuple(value.get("records", self.unit.records)), memory=value.get("memory", self.unit.memory))
                targets.append(episode.compile())
            else:
                targets.append(self.unit.compile())

        def execute(context):
            rows, children, accepted_failures = [], [], []
            for index, (case, target) in enumerate(zip(cases, targets)):
                actual = None
                try:
                    context.check()
                    actual = target._execute(context) if isinstance(target, _Captured) else target._prepared.run(case.get("input"), context)
                    children.append(actual)
                    validations = []
                    for key, expected in case.get("expected", {}).items():
                        observed = actual.ok if key == "ok" else actual.data
                        equal = json.dumps(observed, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
                        validations.append({"ok": equal, "issues": [] if equal else [{"code": "expected_mismatch", "path": key}]})
                    for check in self.checks:
                        context.take()
                        checked = _closed(check(_RunResult(**actual.to_dict()), snapshot(case)), {"ok", "issues", "metrics"}, "check output")
                        if type(checked.get("ok")) is not bool or not isinstance(checked.get("issues", []), list):
                            raise TypeError("A check returns boolean ok and a list of issues")
                        if "metrics" in checked and not isinstance(checked["metrics"], dict):
                            raise TypeError("check metrics must be a JSON dictionary")
                        validations.append(checked)
                        context.check()
                    verdict, judged = None, None
                    if judge is not None:
                        payload = {"input": case.get("input"), "expected": case.get("expected", {}), "result": actual.to_dict(), "rubric": rubric,
                                   "evidence": {"trace": actual.trace(), "tool_events": [e.name for n in actual.walk() for e in n.tool_events]}}
                        judged = judge._prepared.run(payload, context)
                        children.append(judged)
                        verdict = _judge_verdict(judged, actual, rubric)
                    expected_failure = case.get("expected", {}).get("ok") is False
                    ok = (actual.ok or expected_failure) and all(v["ok"] for v in validations) and (verdict is None or verdict["ok"])
                    context.check()
                    if ok and not actual.ok:
                        accepted_failures.append(actual.execution_id)
                    rows.append({"name": case.get("name", str(index)), "ok": ok, "input": case.get("input"), "expected": case.get("expected", {}),
                                 "result": actual.to_dict(), "checks": validations, "judge": verdict,
                                 "candidate_usage": actual.usage, "judge_usage": judged.usage if judged else {}})
                except Exception as exc:
                    failed_row = {"name": case.get("name", str(index)), "ok": False, "input": case.get("input"), "expected": case.get("expected", {}),
                                  "result": actual.to_dict() if actual else None, "error": {"code": type(exc).__name__, "message": str(exc)}}
                    rows.append(failed_row)
                    break
            passed = sum(r["ok"] for r in rows)
            ok = passed == len(cases) and len(rows) == len(cases)
            output = result(self.name, "eval", {"ok": ok, "total": len(cases), "passed": passed, "failed": len(cases) - passed,
                "pass_rate": passed / len(cases), "cases": rows}, children,
                expected_failure_ids=accepted_failures, actions_observed=context.actions,
                judge_mode="deterministic-fixture" if self.judge and (self.judge.runtime is None or self.judge.runtime.provider == "python-runtime") else "model" if self.judge else "none")
            return replace(output, ok=ok, errors=() if ok else (*output.errors, {"code": "eval_failed", "message": "One or more required cases failed"}))

        return _Captured(self.name, "eval", execute, {"name": self.name, "kind": "eval", "cases": len(cases),
            "checks": len(self.checks), "judge": judge.inspect() if judge else None, "rubric": rubric, "unit": self.unit.inspect()})

    def run(self, *, limits=Limits()):
        return self.compile().run(limits=limits)

    async def arun(self, *, limits=Limits()):
        return await self.compile().arun(limits=limits)

    def inspect(self):
        return self.compile().inspect()


