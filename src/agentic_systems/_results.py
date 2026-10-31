"""The single JSON result contract; provider-specific representations stay private."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
import json
import math
import uuid
from pydantic import BaseModel


def _json(value):
    if isinstance(value, BaseModel):
        def finite(item):
            if isinstance(item, BaseModel):
                for name in type(item).model_fields:
                    finite(getattr(item, name))
            elif isinstance(item, dict):
                for child in item.values():
                    finite(child)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    finite(child)
            elif isinstance(item, float) and not math.isfinite(item):
                raise TypeError("Expected finite JSON data")
        finite(value)
        return _json(value.model_dump(mode="json"))
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


def _record_child(output):
    """Keep nested run evidence even when its caller returns a projected dict."""
    from ._context import _active_execution
    active = _active_execution.get()
    if active is not None:
        active.last_result = output
        children = getattr(active, "child_results", None)
        if children is not None and not any(c.execution_id == output.execution_id for c in children):
            children.append(output)
    return output

def _redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if any(t in k.lower() for t in ("api_key", "authorization", "password", "access_token", "secret_key", "session_token")) else _redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    return value


def _preview(value, max_chars=400):
    value = _redact(_json(value))
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value if len(encoded) <= max_chars else {"preview": encoded[:max_chars], "omitted": True}


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
    schema_version: str = "agentic_systems.lineage.v2"
    execution_id: str = ""
    status: str = "completed"

    def to_dict(self):
        return _redact(_json({f.name: getattr(self, f.name) for f in fields(self)}))

    def explain(self):
        return {"execution_id": self.execution_id, "answer": self.answer, "ok": self.ok, "status": self.status, "steps": _json(self.steps)}

    def render(self):
        """Human view of recorded evidence; no generated reasoning or inference."""
        lines = [f"{self.name}: {'PAUSED' if self.status == 'paused' else 'OK' if self.ok else 'FAILED'}", self.answer]
        for step in self.steps[:12]:
            lines.append(f"- {step['title']}: {step['summary']} [{step['step_id']}]")
        if len(self.steps) > 12:
            lines.append(f"{len(self.steps) - 12} more steps; retrieve evidence by execution_id.")
        failed = [s for s in self.steps[12:] if s.get("evidence", {}).get("ok") is False]
        if failed:
            lines.append(f"{len(failed)} failures outside this view: " + ", ".join(s["step_id"] for s in failed[:3]))
        return "\n".join(lines)

    def to_prompt_context(self, *, max_chars=1600):
        if type(max_chars) is not int or max_chars < 1:
            raise ValueError("max_chars must be positive")
        def encode(value):
            return json.dumps(_redact(_json(value)), ensure_ascii=False, separators=(",", ":"))
        failed = [s for s in self.steps if s.get("evidence", {}).get("ok") is False]
        payload = {"ok": self.ok, "steps": [], "omitted_steps": len(self.steps), "failed_steps": len(failed)}
        if self.status == "paused":
            payload["status"] = self.status
        if len(encode(payload)) > max_chars:
            raise ValueError("Context budget is too small for a valid lineage envelope")
        if len(encode({**payload, "execution_id": self.execution_id})) <= max_chars:
            payload["execution_id"] = self.execution_id
        failed_ids = {s["step_id"] for s in failed}
        ordered = [*failed, *(s for s in self.steps if s["step_id"] not in failed_ids)]
        positions = {s["step_id"]: i for i, s in enumerate(self.steps)}
        for step in ordered:
            candidate = {**payload, "steps": [*payload["steps"], step], "omitted_steps": payload["omitted_steps"] - 1}
            if len(encode(candidate)) <= max_chars:
                payload = candidate
        payload["steps"].sort(key=lambda s: positions[s["step_id"]])
        with_answer = {**payload, "answer": self.answer}
        if len(encode(with_answer)) <= max_chars:
            payload = with_answer
        return encode(payload)


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
    status: str = ""
    interrupts: tuple = ()
    continuation: dict | None = None

    def __post_init__(self):
        status = self.status or ("completed" if self.ok else "failed")
        if status not in {"completed", "failed", "paused"}:
            raise ValueError("Unknown execution status")
        if status != "paused":
            status = "completed" if self.ok else "failed"
        elif not self.ok or self.errors or not self.interrupts or not self.continuation:
            raise ValueError("A paused result requires interrupts and a continuation, without errors")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "interrupts", tuple(_json(self.interrupts)))
        object.__setattr__(self, "continuation", _json(self.continuation))
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

    def human_results(self, *, max_steps=8, max_chars=4000):
        """Present observed business work, with one execution ID and bounded data.

        Technical wrappers are omitted; failed operations have priority. Full
        records, IDs and lineage remain available through to_dict/lineage/trace.
        """
        if type(max_steps) is not int or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        if type(max_chars) is not int or max_chars < 256:
            raise ValueError("max_chars must be an integer of at least 256")
        def clipped(value, size):
            text = json.dumps(_redact(_json(value)), ensure_ascii=False, separators=(",", ":"))
            return text if len(text) <= size else text[:max(0, size - 1)] + "…"
        def title(run):
            return str(run.meta.get("name") or run.meta.get("tool_name") or "run").replace("\n", " ")[:80]
        room = max(16, min(500, (max_chars - 160) // 4))
        kind = self.meta.get("kind")
        observed_input = self.meta.get("input")
        shown_output = self.data
        if kind == "environment":
            records = [run.data["row"] for run in self.walk()
                       if run.meta.get("owner_kind") == "environment"
                       and run.meta.get("owner_name") == self.meta.get("name")
                       and run.meta.get("name") == "observe" and "row" in run.data]
            if not records:
                records = [row["record"] for row in self.data.get("history", [])]
            observed_input = {"records_observed": records}
            shown_output = {key: self.data[key] for key in ("outputs", "summary") if key in self.data}
        elif kind == "eval":
            observed_input = {"cases_executed": [row.get("input") for row in self.data.get("cases", [])]}
            shown_output = {key: self.data[key] for key in ("total", "passed", "failed") if key in self.data}
        status = {"completed": "COMPLETED", "failed": "FAILED", "paused": "PAUSED"}[self.status]
        lines = [f"{title(self)}: {status}", "Execution: " + self.execution_id[:80],
                 "Input: " + (clipped(observed_input, room) if observed_input is not None else "not recorded"),
                 "Output: " + clipped(shown_output, room)]
        if self.status == "paused":
            lines.append("Awaiting resume; execution is not complete.")
        if self.errors:
            lines.append("Errors: " + clipped(self.errors, room))
        entries = []
        def collect(run):
            current_kind = run.meta.get("kind")
            internal = run.meta.get("internal") or run.meta.get("owner_kind") in {"environment", "eval"}
            if run is not self and not internal:
                if current_kind in {"agent", "system", "environment", "eval"}:
                    entries.append((not run.ok, current_kind.title() + " " + title(run) + ": " + run.status))
                elif current_kind == "node" and not run.children:
                    entries.append((not run.ok, "Step " + title(run) + ": " + run.status))
                elif not run.ok and not run.children and not run.tool_events:
                    entries.append((True, "Failure " + title(run) + ": failed"))
            for child in run.children:
                collect(child)
            for event in run.tool_events:
                output = event.output
                if isinstance(output, dict) and set(output) == {"data"}:
                    output = output["data"]
                state = "completed" if event.ok else "failed"
                value = output if event.ok else event.error
                entries.append((not event.ok, "Tool " + event.name + ": " + state + " -> " + clipped(value, room)))
            attempts = run.meta.get("scheduler_execution", {}).get("attempt_history", ())
            if len(attempts) > 1:
                for attempt in attempts:
                    entries.append((attempt["status"] != "completed", "Attempt " + str(attempt["number"]) + ": " + attempt["status"]))
            if "next" in run.meta and not internal:
                entries.append((False, "Decision " + title(run) + " -> " + clipped(run.meta["next"], room)))
        collect(self)
        order = sorted(range(len(entries)), key=lambda index: not entries[index][0])
        selected = sorted(order[:max_steps])
        lines.append("Process:")
        shown = 0
        for index in selected:
            line = "- " + entries[index][1]
            if sum(len(value) + 1 for value in lines) + len(line) > max_chars - 80:
                break
            lines.append(line)
            shown += 1
        if shown < len(entries):
            lines.append(str(len(entries) - shown) + " operations omitted; inspect lineage for full evidence.")
        if not entries:
            lines.append("- No business operation recorded.")
        text = "\n".join(lines)
        return text if len(text) <= max_chars else text[:max_chars - 1] + "…"

    def trace(self, mode="compact", *, max_steps=20):
        if mode not in {"compact", "full"}:
            raise ValueError("mode must be compact or full")
        if mode == "full":
            return self.to_dict()
        if type(max_steps) is not int or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        runs = list(self.walk())
        selected = sorted(runs, key=lambda r: r.ok)[:max_steps]
        selected_ids = {r.execution_id for r in selected}
        return {"ok": self.ok, "status": self.status, "execution_id": self.execution_id, "engine": self.engine,
                "model": self.model, "data": _preview(self.data), "errors": _preview(self.errors),
                "omitted_steps": max(0, len(runs) - max_steps),
                "steps": [{"execution_id": r.execution_id, "parent_execution_id": r.parent_execution_id,
                           "name": r.meta.get("name"), "ok": r.ok} for r in runs if r.execution_id in selected_ids]}

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
            important = run is self or run.meta.get("kind") in {"action", "model"} or not run.children
            if important:
                steps.append({"step_id": run.execution_id, "kind": "execution",
                              "title": run.meta.get("name", run.mode), "summary": run.text[:200] or ("completed" if run.ok else "failed"),
                              "source": run.engine, "why": "Recorded execution evidence",
                              "evidence": {"ok": run.ok, "data": _preview(run.data), "errors": _preview(run.errors)}})
            attempts = run.meta.get("scheduler_execution", {}).get("attempt_history", ())
            if len(attempts) > 1 or any(row["status"] != "completed" for row in attempts):
                for attempt in attempts:
                    observed = attempt.get("result", {})
                    steps.append({"step_id": run.execution_id + ":attempt:" + str(attempt["number"]),
                                  "kind": "attempt", "title": "Actor attempt " + str(attempt["number"]),
                                  "summary": attempt["status"], "source": run.engine,
                                  "why": "Observed scheduler attempt; retries retain prior evidence",
                                  "evidence": {"ok": attempt["status"] == "completed",
                                               "usage": observed.get("usage", {}),
                                               "errors": _preview(observed.get("errors", attempt.get("error", [])))}})
            if "next" in run.meta:
                steps.append({"step_id": run.execution_id + ":decision", "kind": "decision", "title": "Next node",
                              "summary": run.meta["next"], "source": run.meta.get("graph_node", "graph"),
                              "why": "Recorded graph routing result", "evidence": {"next": run.meta["next"]}})
            for event in run.tool_events:
                steps.append({"step_id": event.id, "kind": "tool", "title": event.name,
                              "summary": "completed" if event.ok else "failed", "source": event.name,
                              "why": "Recorded Tool event", "evidence": {"ok": event.ok, "output": _preview(limit_rows(_json(event.output))), "error": _preview(event.error)}})
        return _Lineage(name, question if question is not None else json.dumps(_preview(self.meta.get("input")), ensure_ascii=False), goal, self.text[:400] or json.dumps(_preview(self.data), ensure_ascii=False),
                        self.ok, tuple(steps), _json(self.usage), _json(self.validation), tuple(tags or ()), _json(metadata or {}), execution_id=self.execution_id, status=self.status)

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
