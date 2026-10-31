"""LangGraph integration. State contains business data and bounded evidence IDs."""
from __future__ import annotations

from dataclasses import replace
import asyncio
import inspect
import json
import threading
from typing import Annotated, get_type_hints

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from typing_extensions import TypedDict, is_typeddict
from pydantic import BaseModel

from ._context import Context, _active_execution, _scope_context
from ._control import _PauseSignal
from ._results import RunResult, _json, _preview


def _strip(value):
    if isinstance(value, BaseModel):
        _json(value)
        value = value.model_dump(mode="json", exclude_unset=True)
    return {key: item for key, item in value.items() if key != "_lineage"}


def _refs(before, after):
    return list(dict.fromkeys([*before, *after]))[-32:]


def _is_model(schema):
    return isinstance(schema, type) and issubclass(schema, BaseModel)


def _schema_annotations(schema):
    hints = get_type_hints(schema, include_extras=True)
    return {name: hints[name] for name in schema.model_fields} if _is_model(schema) else hints


def _validated_state(schema, value):
    """Validate without putting Pydantic instances or evidence trees in state."""
    if _is_model(schema):
        model = schema.model_validate(value)
        _json(model)  # Reject non-finite data before JSON serializers can mask it.
        return model.model_dump(mode="json", exclude_unset=True)
    return value


class _Evidence:
    """Flat process-local records, separate from checkpoint state."""
    def __init__(self):
        self.records = {}
        self.lock = threading.RLock()

    def put(self, result):
        with self.lock:
            refs = [self.put(child) for child in result.children]
            payload = replace(result, children=(), parent_execution_id=None).to_dict()
            self.records[result.execution_id] = {"result": payload, "children": refs}
            return result.execution_id

    def get(self, key, parent=None):
        with self.lock:
            row = self.records[key]
            payload = {**row["result"], "parent_execution_id": parent,
                       "children": tuple(self.get(ref, key) for ref in row["children"])}
            return RunResult(**payload)

    def roots(self):
        with self.lock:
            nested = {ref for row in self.records.values() for ref in row["children"]}
            return [self.get(ref) for ref in self.records if ref not in nested]

    def summaries(self, refs):
        with self.lock:
            return [{"execution_id": ref, "name": self.records[ref]["result"]["meta"].get("name"),
                     "ok": self.records[ref]["result"]["ok"],
                     "data": _preview(self.records[ref]["result"]["data"], max_chars=300)}
                    for ref in list(dict.fromkeys(refs))[-8:] if ref in self.records]


class _NodeFailure(Exception):
    pass


def _child_roots(scope):
    """Keep recorded calls once when a returned result already contains them."""
    last = (scope.last_result,) if scope.last_result is not None else ()
    candidates = {child.execution_id: child for child in (*scope.child_results, *last)}
    nested = {node.execution_id for child in candidates.values()
              for descendant in child.children for node in descendant.walk()}
    return tuple(child for key, child in candidates.items() if key not in nested)


def _graph_description(builder):
    return {"engine": "langgraph", "state": sorted(_schema_annotations(builder.state_schema)),
            "state_validation": "pydantic" if _is_model(builder.state_schema) else "typed-dict",
            "nodes": list(builder.nodes),
            "edges": [{"source": a, "target": b} for a, b in sorted(builder.edges)],
            "barriers": [{"sources": sorted(a), "target": b} for a, b in sorted(builder.waiting_edges)],
            "decisions": {node: list(branches) for node, branches in builder.branches.items()},
            "lineage": "bounded IDs in state; full records outside checkpoints"}


def _compile_graph(builder, owner_name, *, owner_kind=None):
    if not isinstance(builder, StateGraph) or not (is_typeddict(builder.state_schema) or _is_model(builder.state_schema)):
        raise TypeError("graph must be an uncompiled LangGraph StateGraph with a Pydantic or TypedDict state")
    annotations = _schema_annotations(builder.state_schema)
    if "_lineage" in annotations:
        raise ValueError("_lineage is a reserved, automatically managed evidence channel")
    if builder.context_schema not in {None, Context}:
        raise ValueError("Use toolkit.Context as the graph context schema and pass context= on the owner")
    schema = TypedDict(owner_name + "State", {**annotations, "_lineage": Annotated[list[str], _refs]}, total=False)
    # Typed channels keep the bounded technical lineage separate from user models.
    # Pydantic validators are retained explicitly at every execution boundary.
    graph = StateGraph(schema, context_schema=Context, input_schema=schema, output_schema=schema)

    def adapt(name, spec):
        function = getattr(spec.runnable, "func", None) or getattr(spec.runnable, "afunc", None)
        parameters = inspect.signature(function).parameters if function is not None else {}
        if "runtime" in parameters:
            raise TypeError("Node context uses '*, context: toolkit.Context', not Runtime")
        if "context" in parameters:
            parameter = parameters["context"]
            if parameter.kind is not inspect.Parameter.KEYWORD_ONLY or get_type_hints(function).get("context") is not Context:
                raise TypeError("Injected node context must be keyword-only and annotated toolkit.Context")
        def execute(state, config, runtime):
            from ._grammar import result
            execution = _active_execution.get()
            if execution is None:
                raise RuntimeError("Execute this graph through its Agent, System or Environment")
            step = config.get("metadata", {}).get("langgraph_step", 0)
            scope = execution.at(f"{owner_name}/{name}/{step}")
            scope.frame = execution.frame
            scope.last_result = None
            scope.child_results = []
            node_schema = spec.input_schema if _is_model(spec.input_schema) else builder.state_schema
            business = _validated_state(node_schema, _strip(state))
            memo = scope.memo_key("node", business)
            if memo in scope.journal:
                ref, delta = scope.journal[memo]
                _append(scope, step, name, ref)
                return {**delta, "_lineage": [ref]}
            captured = scope.semantic_snapshots.get(memo)
            if captured is None:
                # A concurrent sibling is not a predecessor, even if it finishes early.
                with scope.lock:
                    refs = [row[2] for row in sorted(scope.frames[scope.frame]) if row[0] < step][-8:]
                captured = _scope_context(scope.semantic, None, lineage=scope.evidence.summaries(refs))
                scope.semantic_snapshots[memo] = captured
            scope.semantic = captured
            token = _active_execution.set(scope)
            recorded = {}
            try:
                if memo not in scope.active_nodes:
                    scope.observe_node()
                    scope.active_nodes.add(memo)
                kwargs = {"context": scope.semantic} if "context" in parameters else {}
                node_input = spec.input_schema.model_validate(business) if _is_model(spec.input_schema) else business
                raw = (asyncio.run(spec.runnable.ainvoke(node_input, config, **kwargs)) if getattr(spec.runnable, "func", None) is None
                       else spec.runnable.invoke(node_input, config, **kwargs))
                command = raw if isinstance(raw, Command) else None
                delta = (command.update or {}) if command is not None else raw
                if isinstance(delta, RunResult):
                    scope.last_result, delta = delta, delta.data
                if isinstance(delta, BaseModel):
                    _json(delta)
                    delta = delta.model_dump(mode="json", exclude_unset=True)
                if not isinstance(delta, dict) or "_lineage" in delta:
                    raise TypeError("A graph node returns a JSON dictionary update; _lineage is managed internally")
                delta = _json(delta)
                normalized = _validated_state(node_schema, {**business, **delta})
                delta = {key: normalized.get(key, value) for key, value in delta.items()}
                recorded = delta
                output = result(name, "node", delta, _child_roots(scope),
                                owner_kind=owner_kind, owner_name=owner_name)
                scope.check()
            except _PauseSignal as signal:
                raise signal.original
            except Exception as exc:
                from langgraph.errors import GraphBubbleUp
                if isinstance(exc, GraphBubbleUp):
                    raise
                output = result(name, "node", recorded, _child_roots(scope), exc,
                                owner_kind=owner_kind, owner_name=owner_name)
                ref = scope.evidence.put(output)
                _append(scope, step, name, ref)
                raise _NodeFailure(str(exc)) from exc
            finally:
                _active_execution.reset(token)
            ref = scope.evidence.put(output)
            _append(scope, step, name, ref)
            if not output.ok:
                raise _NodeFailure("Required node failed: " + name)
            if command is not None:
                return replace(command, update={**delta, "_lineage": [ref]})
            scope.journal[memo] = (ref, delta)
            return {**delta, "_lineage": [ref]}
        execute.__annotations__["runtime"] = Runtime
        return execute

    for name, spec in builder.nodes.items():
        if spec.cache_policy is not None:
            raise ValueError("Node caching is not accepted: it would skip per-run evidence and Context")
        if spec.retry_policy is not None or spec.error_handler_node is not None:
            raise ValueError("SDK retry/error-handler policies require a separate evidence-aware integration")
        graph.add_node(name, adapt(name, spec), defer=spec.defer, metadata=spec.metadata,
                       input_schema=schema, destinations=spec.ends,
                       timeout=spec.timeout, trace_policy=spec.trace_policy)
    for source, target in builder.edges:
        graph.add_edge(source, target)
    for sources, target in builder.waiting_edges:
        graph.add_edge(list(sources), target)
    for source, branches in builder.branches.items():
        for name, branch in branches.items():
            def route(state, config, branch=branch, source=source):
                execution = _active_execution.get()
                execution.check()
                business = _validated_state(builder.state_schema, _strip(state))
                target = branch.path.invoke(builder.state_schema.model_validate(business) if _is_model(builder.state_schema) else business, config)
                execution.check()
                if isinstance(target, str) or isinstance(target, list) and all(isinstance(item, str) for item in target):
                    step = config.get("metadata", {}).get("langgraph_step", 0)
                    with execution.lock:
                        for recorded_step, name, ref in execution.frames[execution.frame]:
                            if recorded_step == step and name == source:
                                execution.evidence.records[ref]["result"]["meta"]["next"] = target
                return target
            route.__name__ = name
            graph.add_conditional_edges(source, route, branch.ends)
    return graph.compile()


def _append(scope, step, name, ref):
    with scope.lock:
        row = (step, name, ref)
        if row not in scope.frames[scope.frame]:
            scope.frames[scope.frame].append(row)


def _observe_state(context, state):
    encoded = json.dumps(_json(state), ensure_ascii=False)
    with context.lock:
        context.state_metrics["snapshots"] += 1
        context.state_metrics["max_bytes"] = max(context.state_metrics["max_bytes"], len(encoded.encode()))
        context.state_metrics["max_lineage_refs"] = max(context.state_metrics["max_lineage_refs"], len(state.get("_lineage", [])))
