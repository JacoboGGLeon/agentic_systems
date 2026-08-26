"""Execution-local capture of delegated Agent results."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .results import RunResult


_ACTIVE_CHILDREN: ContextVar[list[RunResult] | None] = ContextVar(
    "agentic_systems_active_children", default=None
)


@contextmanager
def capture_delegated_results() -> Iterator[list[RunResult]]:
    """Open an execution-local collector for delegated Agent results."""

    children: list[RunResult] = []
    token = _ACTIVE_CHILDREN.set(children)
    try:
        yield children
    finally:
        _ACTIVE_CHILDREN.reset(token)


def record_delegated_result(result: RunResult) -> None:
    """Record a result in the nearest active parent execution, if any."""

    children = _ACTIVE_CHILDREN.get()
    if children is not None:
        children.append(result)
