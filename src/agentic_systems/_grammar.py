"""Agentic Systems 2.1.4: LangGraph state/nodes/edges, scoped execution contracts."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Callable
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

from ._configuration import _Runtime, _Framework, framework
from ._context import Context, Memory, _active_execution, _scope_context, _isolated_memory
from ._contracts import _validate_contract, _validate_policy, _policy_model, _invoke_actor, _check_output, _closed
from ._control import _PauseSignal, _propagate_control
from ._results import RunResult as _RunResult, _json, _record_child
from ._tools import _Skill
from ._langgraph import _Evidence, _compile_graph, _strip, _graph_description, _schema_annotations, _validated_state


def snapshot(value):
    if isinstance(value, BaseModel):
        _json(value)  # Validate finiteness before serialization.
        supplied = value.model_dump(mode="json", exclude_unset=True)
        defaults = value.model_dump(mode="json")
        return snapshot({**{k: v for k, v in defaults.items() if v is not None}, **supplied})
    if isinstance(value, dict):
        return _json({k: snapshot(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return [snapshot(v) for v in value]
    return _json(value)


def identity(value):
    return value


class _RunOptions(BaseModel):
    """Validated root deadline; no node-count quota or public constructor."""
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False, hide_input_in_errors=True)
    timeout_s: StrictFloat | StrictInt | None = Field(default=None, gt=0)


class _ExecutionContext:
    def __init__(self, timeout_s=None, backend="langgraph", *, allow_pause=True):
        self.timeout_s = _RunOptions(timeout_s=timeout_s).timeout_s
        self.started = time.monotonic()
        self.nodes = 0
        self.lock = threading.Lock()
        self.semantic = Context({})
        self.limit_reason = None
        self.backend = backend
        self.allow_pause = allow_pause
        self.in_actor = False
        self.path = ("root",)
        self.elapsed = 0.0
        self.journal = {}
        self.frames = {}
        self.prepared_units = {}
        self.evidence = _Evidence()
        self.outputs = {}
        self.state_metrics = {"snapshots": 0, "max_bytes": 0, "max_lineage_refs": 0}
        self.semantic_snapshots = {}
        self.sources = {}
        self.source_rows = {}
        self.active_nodes = set()

    def at(self, component):
        scope = self.scoped(self.semantic)
        scope.path = (*self.path, component)
        return scope

    def memo_key(self, identity, value):
        encoded = json.dumps(snapshot(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return (*self.path, identity, hashlib.sha256(encoded.encode("utf-8")).hexdigest())

    def begin_segment(self):
        self.started = time.monotonic()

    def end_segment(self):
        self.elapsed += time.monotonic() - self.started

    def close(self):
        for source in self.sources.values():
            close = getattr(source, "close", None)
            if close is not None:
                close()
        self.sources.clear()

    def scoped(self, semantic):
        scoped = object.__new__(_ExecutionScope)
        scoped.parent = self
        scoped.semantic = semantic
        scoped.path = self.path
        scoped.in_actor = self.in_actor
        return scoped

    def check(self):
        if self.timeout_s is not None and self.remaining_s <= 0:
            self.limit_reason = "deadline"
            raise TimeoutError("Shared run deadline exceeded")

    @property
    def remaining_s(self):
        if self.timeout_s is None:
            return None
        return self.timeout_s - self.elapsed - (time.monotonic() - self.started)

    def observe_node(self):
        with self.lock:
            self.check()
            self.nodes += 1


class _ExecutionScope:
    """Read-only semantic scope with a shared deadline and node observations."""

    @property
    def nodes(self):
        return self.parent.nodes

    @property
    def limit_reason(self):
        return self.parent.limit_reason

    def observe_node(self):
        return self.parent.observe_node()

    def check(self):
        return self.parent.check()

    def __getattr__(self, name):
        return getattr(self.parent, name)

    scoped = _ExecutionContext.scoped
    at = _ExecutionContext.at
    memo_key = _ExecutionContext.memo_key


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



def _model_body(owner):
    if not isinstance(owner.runtime, _Runtime):
        raise TypeError("Use runtime(...)")
    if not isinstance(owner.instructions, str):
        raise TypeError("instructions must be a string")
    selected = framework("native") if owner.framework is None else owner.framework
    if not isinstance(selected, _Framework) or selected.name not in {"native", "openai-agents", "strands"}:
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
        from ._engine.core.scheduler import _EXECUTION_DEADLINE
        context.check()
        remaining = context.remaining_s
        deadline_token = _EXECUTION_DEADLINE.set(
            None if remaining is None else time.monotonic() + remaining
        )
        actor_context = context.scoped(context.semantic)
        actor_context.in_actor = True
        token = _active_execution.set(actor_context)
        try:
            child = _invoke_actor(owner, owner.runtime, selected, contract, policy, value)
        finally:
            _active_execution.reset(token)
            _EXECUTION_DEADLINE.reset(deadline_token)
        child = _check_output(child, contract)
        output = result(owner.name, "model", child.data, (child,), framework=selected.name)
        output = replace(output, engine=child.engine, model=child.model)
        try:
            context.check()
            return output
        except Exception as exc:
            return replace(output, ok=False, errors=(*output.errors, {"code": type(exc).__name__, "message": str(exc)}))

    return _Prepared(owner.name, "model", execute, actor=selected.name)



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
class _Prepared:
    name: str
    kind: str
    execute: Callable
    native: Any = None
    description: dict = field(default_factory=dict)
    registry: dict = field(default_factory=dict, compare=False, repr=False)
    actor: str | None = None

    def run(self, value, context):
        memo = context.memo_key("owner:" + self.kind + ":" + self.name, value)
        cached = context.journal.get(memo)
        if isinstance(cached, str):
            return context.evidence.get(cached)
        output = self.execute(snapshot(value), context)
        ref = context.evidence.put(output)
        context.journal[memo] = ref
        return output


def _children(context, frame):
    return [context.evidence.get(ref) for _, _, ref in sorted(context.frames.get(frame, []))]


def _owner_graph(owner, graph, registry, *, initial=identity, project=identity, finish=None, extra=None):
    from ._langgraph import _observe_state
    if not isinstance(owner.name, str) or not owner.name.strip():
        raise ValueError("Owner name is required")
    native = _compile_graph(graph, owner.name, owner_kind=owner.kind)
    fields = set(_schema_annotations(graph.output_schema))
    declared = getattr(owner, "contract", None)
    if getattr(owner, "runtime", None) is not None:
        declared = {k: v for k, v in (declared or {}).items() if k in {"input_schema", "output_schema"}}
    contract = _validate_contract(declared)
    if set(contract) - {"input_schema", "output_schema"}:
        raise ValueError("Graph contracts accept input_schema and output_schema")
    for attribute, cls in (("context", Context), ("memory", Memory)):
        value = getattr(owner, attribute, None)
        if value is not None and not isinstance(value, cls):
            raise TypeError("Use " + cls.__name__ + "(...)")

    def execute(value, context):
        frame = context.memo_key("frame:" + owner.name, value)
        context.frames.setdefault(frame, [])
        captured = context.semantic_snapshots.get(frame)
        if captured is None:
            memory = getattr(owner, "memory", None)
            revision, episodes = memory._snapshot() if memory is not None else (None, [])
            semantic = _scope_context(context.semantic, getattr(owner, "context", None), episodes)
            captured = (semantic, revision)
            context.semantic_snapshots[frame] = captured
        semantic, revision = captured
        scoped = context.scoped(semantic)
        scoped.frame = frame
        token = _active_execution.set(scoped)
        paused, error, business = False, None, {}
        try:
            if "input_schema" in contract:
                from jsonschema import Draft202012Validator
                Draft202012Validator(contract["input_schema"]).validate(value)
            context.check()
            graph_input = _validated_state(graph.input_schema, initial(value))
            # Do not turn internal graph layout into a user-facing quota.
            # Explicit deadlines and actor/episode controls govern termination.
            state = native.invoke(graph_input, config={"recursion_limit": sys.maxsize}, context=scoped.semantic)
            if state.get("__interrupt__"):
                from langgraph.errors import GraphInterrupt
                raise _PauseSignal(GraphInterrupt(tuple(state["__interrupt__"])))
            _observe_state(context, state)
            validated = _validated_state(graph.state_schema, _strip(state))
            projected = _validated_state(graph.output_schema, {k: v for k, v in validated.items() if k in fields})
            business = project(projected, scoped) if project is not identity else projected
            context.check()
        except _PauseSignal:
            paused = True
            raise
        except Exception as exc:
            try:
                _propagate_control(exc)
            except _PauseSignal:
                paused = True
                raise
            error = exc
        finally:
            _active_execution.reset(token)
            if finish is not None and not paused:
                try:
                    finish(scoped)
                except Exception as exc:
                    error = exc
        children = _children(context, frame)
        output = result(owner.name, owner.kind, business, children, error,
                        engine_name="langgraph", input=snapshot(value), internal=description.get("internal", False),
                        lineage_refs=[c.execution_id for c in children],
                        writes=sorted(set().union(*(set(c.data) for c in children))) if project is identity else sorted(business),
                        context={"fingerprint": semantic.fingerprint, "sources": list(semantic.sources),
                                 "memory_revision": revision, "episode_ids": [e["execution_id"] for e in semantic.episodes]})
        if getattr(owner, "runtime", None) is not None:
            actor_result = next((run for child in children for run in child.walk() if run.meta.get("kind") == "model"), None)
            if actor_result is not None:
                output = replace(output, engine=actor_result.engine, model=actor_result.model, mode=actor_result.mode)
        output = _check_output(output, contract)
        if extra is not None:
            output = extra(output, scoped)
        memory = getattr(owner, "memory", None)
        if memory is not None:
            memory.remember(output)
        return output
    description = {"name": owner.name, "kind": owner.kind, "graph": _graph_description(graph)}
    return _Prepared(owner.name, owner.kind, execute, native, description, registry)


class _Executable:
    def compile(self):
        registry = {}
        prepared = self._compile(set(), registry)
        return _Compiled(prepared)

    def inspect(self):
        return self.compile().inspect()

    def __call__(self, state):
        state = snapshot(state)
        active = _active_execution.get()
        if active is None:
            output = self.run(state)
        else:
            prepared = active.prepared_units.get(id(self))
            if prepared is None:
                prepared = self._compile(set(), active.prepared_units)
            output = prepared.run(state, active)
            _record_child(output)
        return {key: value for key, value in output.data.items() if key in output.meta.get("writes", output.data)}


def _nested(graph, seen, registry):
    for spec in graph.nodes.values():
        fn = getattr(spec.runnable, "func", None)
        # LangGraph may retain a callable owner directly or its bound method.
        # Both forms must participate in compile-time validation and cycle checks.
        owner = fn if isinstance(fn, _Executable) else getattr(fn, "__self__", None)
        if isinstance(owner, _Executable):
            owner._compile(seen, registry)


@dataclass(frozen=True)
class _Unit(_Executable):
    name: str
    graph: Any = None
    context: Context | None = field(default=None, kw_only=True)
    memory: Memory | None = field(default=None, kw_only=True)
    contract: dict | None = field(default=None, kw_only=True)
    kind: str = field(default="unit", init=False)

    def _compile(self, seen, registry):
        from langgraph.graph import StateGraph, START, END
        from typing_extensions import TypedDict
        if id(self) in seen:
            raise ValueError("Recursive owner definition")
        if id(self) in registry:
            return registry[id(self)]
        seen = {*seen, id(self)}
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Owner name is required")
        graph = self.graph
        if isinstance(self, Agent):
            if not isinstance(self.skills, tuple) or any(not isinstance(s, _Skill) for s in self.skills):
                raise TypeError("skills must be a tuple of runtime Skills")
            names = [t.name for s in self.skills for t in s.tools]
            if len(set(names)) != len(names):
                raise ValueError("Duplicate Tool identity across Skills")
            if self.runtime is not None and isinstance(self.runtime, _Runtime) and self.runtime.provider == "python-runtime" and len(names) != 1:
                raise ValueError("A Python SDK actor wraps one Tool; declare multi-tool orchestration with graph=Graph(...)")
        if isinstance(self, Agent) and self.runtime is not None:
            actor = _model_body(self)
            class ActorState(TypedDict, total=False):
                input: dict
                output: dict
                result_ref: str
            graph = StateGraph(ActorState)
            def invoke(state):
                active = _active_execution.get()
                current = actor.run(state["input"], active)
                active.last_result = current
                return {"output": current.data, "result_ref": active.evidence.put(current)}
            graph.add_node("actor", invoke)
            graph.add_edge(START, "actor")
            graph.add_edge("actor", END)
            # The actor validates its business contract, not the private transport state.
            prepared = _owner_graph(self, graph, registry, initial=lambda d: {"input": d},
                                    project=lambda s, c: s["output"])
            prepared.description["framework"] = "native" if self.framework is None else self.framework.name
        else:
            if not isinstance(graph, StateGraph):
                raise TypeError("Pass graph=Graph(...); orchestration is LangGraph only")
            _nested(graph, seen, registry)
            prepared = _owner_graph(self, graph, registry)
        registry[id(self)] = prepared
        return prepared

    def run(self, input=None, *, timeout_s=None):
        active = _active_execution.get()
        if active is not None:
            if timeout_s is not None:
                raise ValueError("Nested runs inherit the root deadline")
            prepared = active.prepared_units.get(id(self)) or self._compile(set(), active.prepared_units)
            return _record_child(prepared.run(input, active))
        return self.compile().run(input, timeout_s=timeout_s)

    async def arun(self, input=None, *, timeout_s=None):
        return await asyncio.to_thread(self.run, input, timeout_s=timeout_s)


@dataclass(frozen=True)
class Agent(_Unit):
    skills: tuple = ()
    runtime: Any = None
    framework: Any = None
    instructions: str = ""
    policy: dict | BaseModel | None = None
    kind: str = field(default="agent", init=False)

    def __post_init__(self):
        if (self.graph is None) == (self.runtime is None):
            raise ValueError("Agent needs graph=Graph(...) or an explicit runtime")
        if self.runtime is None and (self.framework is not None or self.instructions or self.policy is not None):
            raise ValueError("Actor SDK options require runtime; graph operators execute Python directly")
        if self.policy is not None:
            object.__setattr__(self, "policy", _policy_model(self.policy))


@dataclass(frozen=True)
class System(_Unit):
    kind: str = field(default="system", init=False)


@dataclass(frozen=True)
class _Compiled:
    _prepared: _Prepared
    _driver: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        from ._continuation import _Driver
        object.__setattr__(self, "_driver", _Driver(self._prepared))

    def run(self, input=None, *, timeout_s=None):
        active = _active_execution.get()
        if active is not None:
            if timeout_s is not None:
                raise ValueError("Nested runs inherit the root deadline")
            return _record_child(self._prepared.run(input, active))
        context = _ExecutionContext(timeout_s,
                                    allow_pause=self._prepared.kind != "eval")
        context.prepared_units = self._prepared.registry
        try:
            return _boundary(self._driver.start({} if input is None else input, context))
        except (TypeError, ValueError) as exc:
            return result(self._prepared.name, self._prepared.kind, {}, error=exc)

    async def arun(self, input=None, *, timeout_s=None):
        return await asyncio.to_thread(self.run, input, timeout_s=timeout_s)

    def resume(self, paused, value):
        return _boundary(self._driver.resume(paused, value))

    async def aresume(self, paused, value):
        return await asyncio.to_thread(self.resume, paused, value)

    def inspect(self):
        return snapshot({**self._prepared.description, "continuations": "process-local",
                         "checkpoint_state": "business data + bounded lineage references"})


def _boundary(output):
    validation = output.check_invariants()
    if not validation.ok:
        return replace(output, status="failed", ok=False, continuation=None,
                       errors=(*output.errors, {"code": "invariant_failed", "issues": validation.to_dict()["issues"]}))
    return output


@dataclass(frozen=True)
class Environment(_Executable):
    name: str
    graph: Any
    records: Any
    max_steps: int | None = None
    state: Any = None
    observe: Callable | None = None
    update: Callable | None = None
    stop: Callable | None = None
    context: Context | None = field(default=None, kw_only=True)
    memory: Memory | None = field(default=None, kw_only=True)
    kind: str = field(default="environment", init=False)

    def _compile(self, seen, registry):
        from langgraph.graph import StateGraph, START, END
        from typing_extensions import TypedDict
        if id(self) in seen:
            raise ValueError("Recursive Environment")
        if id(self) in registry:
            return registry[id(self)]
        if not callable(self.records) and (not isinstance(self.records, tuple) or not self.records):
            raise ValueError("records must be a nonempty tuple or a lazy factory")
        if self.max_steps is not None and (type(self.max_steps) is not int or self.max_steps < 1):
            raise ValueError("max_steps is None or a positive ceiling")
        if any(fn is not None and not callable(fn) for fn in (self.observe, self.update, self.stop)):
            raise TypeError("Environment callbacks must be callable")
        step = System(self.name + ":step", self.graph)._compile({*seen, id(self)}, registry)
        step.description["internal"] = True
        records = None if callable(self.records) else snapshot(self.records)
        initial = snapshot({} if self.state is None else self.state)
        class EpisodeState(TypedDict, total=False):
            state: dict
            index: int
            row: dict
            value: dict
            child_ref: str
            reason: str
        graph = StateGraph(EpisodeState)
        def storage(active):
            return active.outputs.setdefault((active.frame, "episode"), {"state": initial, "history": [], "refs": [], "reason": ""})
        def observe(state):
            active = _active_execution.get()
            stored = storage(active)
            index = state["index"]
            if self.max_steps is not None and index >= self.max_steps:
                reason = "records_exhausted" if records is not None and index >= len(records) else "step_limit"
                stored["reason"] = reason
                return {"reason": reason}
            key = (active.frame, "source")
            if key not in active.sources:
                active.sources[key] = iter(self.records() if records is None else records)
            try:
                row = snapshot(next(active.sources[key]))
            except StopIteration:
                stored["reason"] = "records_exhausted"
                return {"reason": "records_exhausted"}
            value = self.observe(snapshot(row), snapshot(state["state"])) if self.observe else row
            return {"row": row, "value": snapshot(value)}
        def run(state):
            active = _active_execution.get()
            output = step.run(state["value"], active)
            ref = active.evidence.put(output)
            stored = storage(active)
            if ref not in stored["refs"]:
                stored["refs"].append(ref)
            _record_child(output)
            return {"child_ref": ref}
        def update(state):
            active = _active_execution.get()
            output = active.evidence.get(state["child_ref"])
            after = self.update(snapshot(state["state"]), snapshot(state["row"]), output) if self.update else ({"processed": state["index"] + 1} if self.state is None else state["state"])
            after = snapshot(after)
            stopped = self.stop(snapshot(after), output) if self.stop else False
            if type(stopped) is not bool:
                raise TypeError("stop must return bool")
            stored = storage(active)
            stored["state"] = after
            stored["history"].append({"step": state["index"], "record": state["row"], "state_before": state["state"],
                                      "state_after": after, "execution_id": output.execution_id})
            stored["reason"] = "stop" if stopped else ""
            return {"state": after, "index": state["index"] + 1, "reason": stored["reason"]}
        graph.add_node("observe", observe)
        graph.add_node("run", run)
        graph.add_node("update", update)
        graph.add_edge(START, "observe")
        graph.add_conditional_edges("observe", lambda s: END if s.get("reason") else "run", [END, "run"])
        graph.add_edge("run", "update")
        graph.add_conditional_edges("update", lambda s: END if s.get("reason") else "observe", [END, "observe"])
        def finish(active):
            iterator = active.sources.pop((active.frame, "source"), None)
            close = getattr(iterator, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    storage(active)["reason"] = "source_close_failed"
                    raise
        def extra(output, active):
            stored = storage(active)
            reason = stored["reason"] or ("execution_limit" if active.limit_reason else "unit_failed")
            data = {"outputs": [active.evidence.records[ref]["result"]["data"] for ref in stored["refs"]],
                    "history": stored["history"], "summary": {"state": stored["state"], "processed": len(stored["refs"]),
                    "terminated": reason in {"stop", "records_exhausted"}, "truncated": reason in {"step_limit", "execution_limit"}, "reason": reason}}
            return replace(output, data=data, meta={**output.meta, "writes": sorted(data)})
        prepared = _owner_graph(self, graph, registry, initial=lambda value: {"state": initial, "index": 0, "reason": ""},
                                finish=finish, extra=extra)
        prepared.description["episode_graph"] = step.description["graph"]
        prepared.description["records"] = "lazy" if records is None else len(records)
        registry[id(self)] = prepared
        return prepared

    def run(self, *, timeout_s=None):
        return self.compile().run({}, timeout_s=timeout_s)

    async def arun(self, *, timeout_s=None):
        return await asyncio.to_thread(self.run, timeout_s=timeout_s)


@dataclass(frozen=True)
class Eval(_Executable):
    name: str
    unit: Any
    cases: tuple
    checks: tuple = ()
    judge: Agent | None = None
    rubric: dict | None = None
    kind: str = field(default="eval", init=False)

    def _compile(self, seen, registry):
        from langgraph.graph import StateGraph, START, END
        from typing_extensions import TypedDict
        if not isinstance(self.unit, (_Unit, Environment)):
            raise TypeError("Eval targets Agent, System or Environment")
        if not isinstance(self.cases, tuple) or not self.cases:
            raise ValueError("Eval needs a nonempty tuple of cases")
        if not isinstance(self.checks, tuple) or any(not callable(c) for c in self.checks):
            raise TypeError("checks must be a tuple of callables")
        if self.judge is None and self.rubric is not None:
            raise ValueError("A rubric needs a judge")
        rubric = _rubric(self.rubric) if self.judge else None
        judge = self.judge._compile(seen, registry) if self.judge else None
        cases = snapshot(self.cases)
        targets = []
        for case in cases:
            _closed(case, {"name", "input", "expected"}, "case")
            expected = _closed(case.get("expected"), {"ok", "data"}, "expected")
            if not expected and not self.checks and judge is None:
                raise ValueError("A case needs expected, checks or judge")
            target = self.unit
            if isinstance(target, Environment):
                values = _closed(case.get("input"), {"records", "state"}, "episode input")
                target = replace(target, records=tuple(values.get("records", target.records)), state=values.get("state", target.state))
            targets.append(target._compile(seen, registry))
        class EvalState(TypedDict):
            index: int
        graph = StateGraph(EvalState)
        def evaluate_case(state):
            active = _active_execution.get()
            active.allow_pause = False
            index = state["index"]
            case = cases[index]
            actual = targets[index].run(case.get("input") if not isinstance(self.unit, Environment) else {}, active)
            checked = []
            for key, expected in case.get("expected", {}).items():
                observed = actual.ok if key == "ok" else actual.data
                checked.append({"ok": observed == expected, "path": key})
            for check in self.checks:
                verdict = _closed(check(_RunResult(**actual.to_dict()), snapshot(case)), {"ok", "issues", "metrics"}, "check")
                if type(verdict.get("ok")) is not bool:
                    raise TypeError("A check returns a boolean ok")
                checked.append(verdict)
            verdict, judged = None, None
            if judge is not None:
                judged = judge.run({"input": case.get("input"), "expected": case.get("expected", {}),
                                    "result": actual.to_dict(), "rubric": rubric}, active.at("judge"))
                verdict = _judge_verdict(judged, actual, rubric)
            accepted_failure = case.get("expected", {}).get("ok") is False
            ok = (actual.ok or accepted_failure) and all(c["ok"] for c in checked) and (verdict is None or verdict["ok"])
            rows = active.outputs.setdefault((active.frame, "eval"), [])
            rows.append({"name": case.get("name", str(index)), "ok": ok, "input": case.get("input"),
                         "execution_id": actual.execution_id, "checks": checked, "judge": verdict})
            evidence = (actual,) if judged is None else (actual, judged)
            outcome = result(self.name + ":case:" + str(index), "eval-case", {"index": index + 1}, evidence,
                             expected_failure_ids=[actual.execution_id] if accepted_failure and ok else [])
            return replace(outcome, ok=ok, errors=() if ok else (*outcome.errors, {"code": "eval_failed"}))
        def evaluate(state):
            with _isolated_memory():
                return evaluate_case(state)
        graph.add_node("evaluate", evaluate)
        graph.add_edge(START, "evaluate")
        graph.add_conditional_edges("evaluate", lambda s: "evaluate" if s["index"] < len(cases) else END, ["evaluate", END])
        def extra(output, active):
            rows = active.outputs.get((active.frame, "eval"), [])
            passed = sum(row["ok"] for row in rows)
            ok = passed == len(cases)
            return replace(output, ok=ok, status="completed" if ok else "failed",
                data={"total": len(cases), "passed": passed, "failed": len(cases)-passed, "cases": rows},
                meta={**output.meta, "writes": ["total", "passed", "failed", "cases"], "memory_isolation": "per_case"},
                errors=() if ok else (*output.errors, {"code": "eval_failed"}))
        prepared = _owner_graph(self, graph, registry, initial=lambda value: {"index": 0}, extra=extra)
        registry[id(self)] = prepared
        return prepared

    def run(self, *, timeout_s=None):
        return self.compile().run({}, timeout_s=timeout_s)

    async def arun(self, *, timeout_s=None):
        return await asyncio.to_thread(self.run, timeout_s=timeout_s)
