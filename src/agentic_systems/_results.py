"""The single JSON result contract; provider-specific representations stay private."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
import json
import math
import uuid


def _json(value):
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("JSON keys must be strings")
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    if type(value) in {str, int, bool, type(None)}:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise TypeError("Expected finite JSON data")


def _redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if any(t in k.lower() for t in ("api_key", "authorization", "password", "access_token", "secret_key", "session_token")) else _redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    return value


@dataclass(frozen=True)
class _Event:
    id: str
    name: str
    input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    ok: bool = True
    error: dict | None = None
    duration_ms: float | None = None
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class _Validation:
    ok: bool = True
    issues: tuple = ()

    def to_dict(self):
        return {"ok": self.ok, "issues": _json(self.issues)}


@dataclass(frozen=True)
class _Lineage:
    name: str
    question: str
    goal: str
    answer: str
    ok: bool
    steps: tuple
    usage: dict
    validation: dict | None
    tags: tuple
    metadata: dict
    schema_version: str = "agentic_systems.lineage.v1"

    def to_dict(self):
        return _redact(_json({f.name: getattr(self, f.name) for f in fields(self)}))

    def explain(self):
        return {"answer": self.answer, "ok": self.ok, "steps": _json(self.steps)}

    def to_prompt_context(self, *, max_chars=1600):
        if type(max_chars) is not int or max_chars < 1:
            raise ValueError("max_chars must be positive")
        return json.dumps(self.explain(), ensure_ascii=False, separators=(",", ":"))[:max_chars]


@dataclass(frozen=True)
class RunResult:
    text: str = ""
    final: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)
    ok: bool = True
    messages: tuple = ()
    tool_events: tuple = ()
    raw_responses: tuple = ()
    usage: dict = field(default_factory=dict)
    engine: str = "python-runtime"
    model: str = ""
    mode: str = "default"
    trace_schema_version: str = "agentic_systems.trace.v1"
    validation: dict | None = None
    errors: tuple = ()
    meta: dict = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: "run-" + uuid.uuid4().hex)
    parent_execution_id: str | None = None
    children: tuple = ()

    def __post_init__(self):
        if type(self.ok) is not bool or not isinstance(self.data, dict):
            raise TypeError("RunResult requires boolean ok and dictionary data")
        children = tuple(RunResult(**v) if isinstance(v, dict) else v for v in self.children)
        if any(not isinstance(c, RunResult) for c in children):
            raise TypeError("children must contain RunResult values")
        events = tuple(_Event(**v) if isinstance(v, dict) else v for v in self.tool_events)
        if any(not isinstance(e, _Event) for e in events):
            raise TypeError("tool_events must contain event records")
        events = tuple(_Event(**_redact(_json({f.name: getattr(e, f.name) for f in fields(e)}))) for e in events)
        object.__setattr__(self, "children", children)
        object.__setattr__(self, "tool_events", events)
        for name in ("data", "final", "usage", "meta", "messages", "raw_responses", "validation", "errors"):
            value = _redact(_json(getattr(self, name)))
            object.__setattr__(self, name, tuple(value) if name in {"messages", "raw_responses", "errors"} else value)

    def to_dict(self):
        payload = {f.name: getattr(self, f.name) for f in fields(self) if f.name not in {"children", "tool_events"}}
        payload["children"] = [c.to_dict() for c in self.children]
        payload["tool_events"] = [{f.name: getattr(e, f.name) for f in fields(e)} for e in self.tool_events]
        return _redact(_json(payload))

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def trace(self, mode="compact"):
        if mode not in {"compact", "full"}:
            raise ValueError("mode must be compact or full")
        if mode == "full":
            return self.to_dict()
        return {"ok": self.ok, "execution_id": self.execution_id, "engine": self.engine,
                "model": self.model, "data": _json(self.data), "errors": _json(self.errors),
                "steps": [{"execution_id": r.execution_id, "parent_execution_id": r.parent_execution_id,
                           "name": r.meta.get("name"), "ok": r.ok} for r in self.walk()]}

    def lineage(self, *, name="run", question=None, goal="", tags=None, metadata=None, max_tool_rows=3):
        if type(max_tool_rows) is not int or max_tool_rows < 0:
            raise ValueError("max_tool_rows must be nonnegative")
        steps = []
        def limit_rows(value):
            if isinstance(value, list):
                return [limit_rows(v) for v in value[:max_tool_rows]]
            if isinstance(value, dict):
                return {k: limit_rows(v) for k, v in value.items()}
            return value
        for run in self.walk():
            steps.append({"step_id": run.execution_id, "kind": "execution",
                          "title": run.meta.get("name", run.mode), "summary": run.text,
                          "source": run.engine, "why": "Recorded execution evidence",
                          "evidence": {"ok": run.ok, "data": _json(run.data), "errors": _json(run.errors)}})
            if "next" in run.meta:
                steps.append({"step_id": run.execution_id + ":decision", "kind": "decision", "title": "Next node",
                              "summary": run.meta["next"], "source": run.meta.get("graph_node", "graph"),
                              "why": "Recorded graph routing result", "evidence": {"next": run.meta["next"]}})
            for event in run.tool_events:
                steps.append({"step_id": event.id, "kind": "tool", "title": event.name,
                              "summary": "completed" if event.ok else "failed", "source": event.name,
                              "why": "Recorded Tool event", "evidence": limit_rows(_json(event.output))})
        return _Lineage(name, question if question is not None else json.dumps(self.meta.get("input"), ensure_ascii=False), goal, self.text or json.dumps(self.data, ensure_ascii=False),
                        self.ok, tuple(steps), _json(self.usage), _json(self.validation), tuple(tags or ()), _json(metadata or {}))

    def check_invariants(self):
        issues, ids, events = [], set(), set()
        allowed_ids = set(self.meta.get("allowed_error_ids", ()))
        for run in self.walk():
            if run.execution_id in ids:
                issues.append({"code": "duplicate_execution_id", "path": run.execution_id})
            ids.add(run.execution_id)
            accepted = set(run.meta.get("expected_failure_ids", ()))
            if run.ok and run.execution_id not in allowed_ids and (run.errors or any(not c.ok and c.execution_id not in accepted for c in run.children)):
                issues.append({"code": "success_with_failed_evidence", "path": run.execution_id})
            for child in run.children:
                if child.parent_execution_id != run.execution_id:
                    issues.append({"code": "parent_mismatch", "path": child.execution_id})
            for event in run.tool_events:
                if event.id in events or event.ok and event.error:
                    issues.append({"code": "inconsistent_tool_event", "path": event.id})
                events.add(event.id)
            if any(isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0 for v in run.usage.values()):
                issues.append({"code": "negative_usage", "path": run.execution_id})
        return _Validation(not issues, tuple(issues))


def _from_engine(value):
    payload = value.to_dict()
    payload["execution_id"] = payload.get("execution_id") or "run-" + uuid.uuid4().hex
    payload["children"] = [_from_engine(c).to_dict() for c in value.children]
    for child in payload["children"]:
        child["parent_execution_id"] = payload["execution_id"]
    usage = payload.setdefault("usage", {})
    usage["inference_requests"] = 0 if value.engine == "python-runtime" else usage.get("inference_requests", usage.get("requests", 0))
    usage["tool_calls"] = len(value.tool_events)
    return RunResult(**payload)
