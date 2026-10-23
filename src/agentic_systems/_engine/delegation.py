"""Execution-local capture of delegated Agent results."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .results import RunResult


_ACTIVE_CHILDREN: ContextVar[list[RunResult] | None] = ContextVar(
    "agentic_systems_active_children", default=None
)
_INLINE_DELEGATED_SCHEDULER: ContextVar[bool] = ContextVar(
    "agentic_systems_inline_delegated_scheduler", default=False
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


@contextmanager
def inline_delegated_scheduler() -> Iterator[None]:
    """Keep a delegated Agent on the parent scheduler's active execution lane.

    Framework SDKs may invoke synchronous tools from their own worker thread.
    Marking the delegation at the tool boundary prevents that child from
    submitting back into the parent's single-worker executor and deadlocking.
    The parent execution still owns the end-to-end timeout.
    """

    token = _INLINE_DELEGATED_SCHEDULER.set(True)
    try:
        yield
    finally:
        _INLINE_DELEGATED_SCHEDULER.reset(token)


def delegated_scheduler_is_inline() -> bool:
    return _INLINE_DELEGATED_SCHEDULER.get()


def record_delegated_result(result: RunResult) -> None:
    """Record a result in the nearest active parent execution, if any."""

    children = _ACTIVE_CHILDREN.get()
    if children is not None:
        children.append(result)
