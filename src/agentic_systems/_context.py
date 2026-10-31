"""Semantic snapshots and explicit, process-local episodic memory."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import hashlib
import json
import threading

from ._results import RunResult, _json, _redact


_active_execution = ContextVar("agentic_execution", default=None)
_memory_scope = ContextVar("agentic_memory_scope", default=None)


@contextmanager
def _isolated_memory():
    scope = {"parent": _memory_scope.get(), "views": {}, "lock": threading.RLock()}
    token = _memory_scope.set(scope)
    try:
        yield
    finally:
        _memory_scope.reset(token)



def _encode(value):
    return json.dumps(_redact(_json(value)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, init=False)
class Context:
    """A detached JSON snapshot of domain information, sources and selected episodes.

    It contains reference data, never executable instructions or service clients.
    Returned dictionaries are detached copies; modifying them cannot alter a run.
    """

    _payload: str = field(repr=False)
    _sources: str = field(repr=False)
    _episodes: str = field(default="[]", repr=False)
    _lineage: str = field(default="[]", repr=False)

    def __init__(self, data, *, sources=()):
        data = _json(data)
        if not isinstance(data, dict):
            raise TypeError("Context data must be a JSON dictionary")
        if not isinstance(sources, tuple) or any(not isinstance(s, str) or not s for s in sources):
            raise TypeError("Context sources must be a tuple of nonempty source identifiers")
        object.__setattr__(self, "_payload", _encode(data))
        object.__setattr__(self, "_sources", _encode(sources))
        object.__setattr__(self, "_episodes", "[]")
        object.__setattr__(self, "_lineage", "[]")

    @property
    def data(self):
        return json.loads(self._payload)

    @property
    def sources(self):
        return tuple(json.loads(self._sources))

    @property
    def episodes(self):
        return json.loads(self._episodes)

    @property
    def lineage(self):
        """At most eight compact observations of preceding execution evidence."""
        return json.loads(self._lineage)

    @property
    def fingerprint(self):
        return hashlib.sha256(_encode(self.to_dict()).encode("utf-8")).hexdigest()

    def to_dict(self):
        return {"data": self.data, "sources": list(self.sources), "episodes": self.episodes, "lineage": self.lineage}


def _scope_context(parent, declared, episodes=(), *, lineage=()):
    local = parent if declared is None else declared
    data = parent.data
    for key, value in local.data.items():
        if key in data and _encode(data[key]) != _encode(value):
            raise ValueError("Conflicting Context key: " + key)
        data[key] = value
    selected = Context(data, sources=tuple(dict.fromkeys((*parent.sources, *local.sources))))
    previous = {entry["execution_id"]: entry for entry in (*parent.episodes, *episodes)}
    object.__setattr__(selected, "_episodes", _encode(list(previous.values())))
    evidence = {entry["execution_id"]: entry for entry in (*parent.lineage, *lineage)}
    object.__setattr__(selected, "_lineage", _encode(list(evidence.values())[-8:]))
    return selected


class Memory:
    """Bounded, in-process episodic memory. Persistence and semantic facts are separate.

    Attach to one Agent/System to read a snapshot at entry and remember its outcome.
    Successful and failed executions are retained; a failure is never learned as truth.
    """

    def __init__(self, *, capacity=20):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("Memory capacity must be a positive integer")
        self.capacity = capacity
        self._entries = []
        self._revision = 0
        self._lock = threading.RLock()
        self._is_view = False

    def _view_in(self, scope):
        if scope is None or self._is_view:
            return self
        with scope["lock"]:
            key = id(self)
            if key not in scope["views"]:
                source = self._view_in(scope["parent"])
                with source._lock:
                    view = Memory(capacity=source.capacity)
                    view._entries = json.loads(_encode(source._entries))
                    view._revision = source._revision
                    view._is_view = True
                scope["views"][key] = view
            return scope["views"][key]

    def read(self):
        view = self._view_in(_memory_scope.get())
        if view is not self:
            return view.read()
        with self._lock:
            return json.loads(_encode(self._entries))

    def _snapshot(self):
        view = self._view_in(_memory_scope.get())
        if view is not self:
            return view._snapshot()
        with self._lock:
            return self._revision, self.read()

    def remember(self, result):
        view = self._view_in(_memory_scope.get())
        if view is not self:
            return view.remember(result)
        if not isinstance(result, RunResult):
            raise TypeError("Memory remembers public RunResult values")
        with self._lock:
            for entry in self._entries:
                if entry["execution_id"] == result.execution_id:
                    return
            self._revision += 1
            self._entries.append({"execution_id": result.execution_id, "revision": self._revision,
                                  "ok": result.ok, "context": result.meta.get("context", {}),
                                  "lineage": json.loads(result.lineage().to_prompt_context())})
            self._entries = self._entries[-self.capacity:]
