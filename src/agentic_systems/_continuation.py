"""Process-local LangGraph continuations; execution resources never enter state."""
from __future__ import annotations

import threading
import uuid

from ._control import _PauseSignal
from typing_extensions import TypedDict
from ._results import RunResult, _json


class _DriverState(TypedDict, total=False):
    input: dict
    result_ref: str


class _Driver:
    def __init__(self, prepared):
        from langgraph.graph import StateGraph, START, END
        from langgraph.runtime import Runtime
        from langgraph.checkpoint.memory import InMemorySaver

        self.prepared = prepared
        self.identity = uuid.uuid4().hex
        self.sessions = {}
        self.lock = threading.Lock()
        def execute(state, runtime):
            try:
                output = prepared.run(state["input"], runtime.context["execution"])
                return {"result_ref": runtime.context["execution"].evidence.put(output)}
            except _PauseSignal as signal:
                raise signal.original
        execute.__annotations__["runtime"] = Runtime
        builder = StateGraph(_DriverState)
        builder.add_node("execute", execute)
        builder.add_edge(START, "execute")
        builder.add_edge("execute", END)
        self.saver = InMemorySaver()
        self.graph = builder.compile(checkpointer=self.saver)

    def start(self, value, context):
        key = uuid.uuid4().hex
        session = {"context": context, "input": _json(value), "generation": 0, "busy": True}
        with self.lock:
            self.sessions[key] = session
        return self._invoke(key, {"input": value})

    def resume(self, paused, value):
        from langgraph.types import Command
        if not isinstance(paused, RunResult) or paused.status != "paused":
            raise ValueError("resume requires a paused RunResult")
        handle = paused.continuation
        if handle.get("program") != self.identity:
            raise ValueError("Continuation belongs to another compiled program")
        answer = _json(value)
        with self.lock:
            session = self.sessions.get(handle.get("session"))
            if session is None or session["generation"] != handle.get("generation") or session.get("paused_id") != paused.execution_id:
                raise ValueError("Continuation is stale or completed")
            if session["busy"]:
                raise ValueError("Continuation is already running")
            session["busy"] = True
        return self._invoke(handle["session"], Command(resume=answer))

    def _invoke(self, key, argument):
        session = self.sessions[key]
        context = session["context"]
        context.begin_segment()
        config = {"configurable": {"thread_id": key}}
        keep_session = False
        try:
            context.check()
            state = self.graph.invoke(argument, config=config, context={"execution": context})
            interrupts = state.get("__interrupt__", ())
            if interrupts:
                session["generation"] += 1
                runs = context.evidence.roots()
                descendants = {c.execution_id for r in runs for c in list(r.walk())[1:]}
                roots = {r.execution_id: r for r in runs if r.execution_id not in descendants}
                usage = {}
                for run in roots.values():
                    for name, count in run.usage.items():
                        if type(count) in {int, float}:
                            usage[name] = usage.get(name, 0) + count
                failed = [r for r in roots.values() if not r.ok]
                output = RunResult(ok=not failed, status="failed" if failed else "paused", data={}, children=tuple(roots.values()), usage=usage,
                    errors=tuple(error for run in failed for error in run.errors),
                    interrupts=tuple({"id": i.id, "value": _json(i.value)} for i in interrupts),
                    continuation=None if failed else {"program": self.identity, "session": key, "generation": session["generation"]},
                    meta={"name": self.prepared.name, "kind": self.prepared.kind, "backend": "langgraph",
                          "nodes_observed": context.nodes, "input": session["input"],
                          "resumes_execution_id": session.get("paused_id")})
                from dataclasses import replace
                output = replace(output, children=tuple(replace(c, parent_execution_id=output.execution_id) for c in output.children))
                keep_session = not failed
                session["paused_id"] = output.execution_id
                return output
            output = context.evidence.get(state["result_ref"])
            from dataclasses import replace
            return replace(output, meta={**output.meta, "nodes_observed": context.nodes,
                           "input": session["input"], "state_metrics": context.state_metrics, "resumes_execution_id": session.get("paused_id")})
        except Exception as exc:
            return RunResult(ok=False, errors=({"code": type(exc).__name__, "message": str(exc)},),
                             meta={"name": self.prepared.name, "backend": "langgraph", "nodes_observed": context.nodes})
        finally:
            context.end_segment()
            with self.lock:
                session["busy"] = False
                if not keep_session:
                    self.sessions.pop(key, None)
                    context.close()
                    self.saver.delete_thread(key)
