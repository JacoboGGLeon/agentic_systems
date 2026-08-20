"""Shared execution contracts for Agentic Systems 2.0.

These contracts describe behavior rather than a specific framework. Agents,
graphs, pipelines and compiled systems can therefore share one public boundary.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .results import RunResult


@runtime_checkable
class Executable(Protocol):
    """Anything that executes an input and returns a RunResult."""

    def run(self, input: Any = None, **kwargs: Any) -> RunResult:
        """Execute synchronously."""


@runtime_checkable
class AsyncExecutable(Executable, Protocol):
    """An Executable with native asynchronous execution."""

    def arun(self, input: Any = None, **kwargs: Any) -> Awaitable[RunResult]:
        """Execute asynchronously."""


@runtime_checkable
class ExecutionPlan(Protocol):
    """Strategy that orders and connects executable units in a system."""

    @property
    def name(self) -> str:
        """Stable plan name used in traces and inspection."""

    def execute(
        self,
        units: Iterable[Executable],
        input: Any = None,
        **kwargs: Any,
    ) -> RunResult:
        """Execute connected units and return one hierarchical result."""


def is_executable(value: Any) -> bool:
    """Return whether value implements the minimal execution contract."""

    return isinstance(value, Executable)


def coerce_run_result(
    value: Any,
    *,
    engine: str = "python-runtime",
    model: str = "",
    mode: str = "default",
) -> RunResult:
    """Normalize a custom executable output at the public boundary."""

    if isinstance(value, RunResult):
        return value
    if isinstance(value, dict):
        return RunResult(data=value, engine=engine, model=model, mode=mode)
    if value is None:
        return RunResult(engine=engine, model=model, mode=mode)
    return RunResult(text=str(value), engine=engine, model=model, mode=mode)


@dataclass(frozen=True)
class CallableExecutable:
    """Adapt a Python callable to the Executable contract."""

    function: Callable[..., Any]
    name: str = "callable"
    engine: str = "python-runtime"
    model: str = ""

    def run(self, input: Any = None, **kwargs: Any) -> RunResult:
        value = self.function(input, **kwargs)
        result = coerce_run_result(value, engine=self.engine, model=self.model)
        result.meta.setdefault("executable", self.name)
        return result


@dataclass(frozen=True)
class SequentialPlan:
    """Deterministic left-to-right execution plan."""

    name: str = "sequential"
    stop_on_error: bool = True
    input_selector: Callable[[RunResult], Any] | None = field(
        default=None, repr=False, compare=False
    )

    def execute(
        self,
        units: Iterable[Executable],
        input: Any = None,
        **kwargs: Any,
    ) -> RunResult:
        current = input
        children: list[RunResult] = []
        for unit in units:
            child = coerce_run_result(unit.run(current, **kwargs))
            children.append(child)
            if self.stop_on_error and not child.ok:
                break
            if self.input_selector is not None:
                current = self.input_selector(child)
            elif child.data:
                current = child.data
            elif child.text:
                current = child.text
            else:
                current = child.final

        final = children[-1] if children else coerce_run_result(input)
        return RunResult(
            text=final.text,
            final=dict(final.final),
            data=dict(final.data),
            ok=all(child.ok for child in children),
            messages=[message for child in children for message in child.messages],
            tool_events=[event for child in children for event in child.tool_events],
            raw_responses=[item for child in children for item in child.raw_responses],
            usage=_sum_usage(children),
            engine="agentic-system",
            model=final.model,
            mode=final.mode,
            children=children,
            meta={"execution_plan": self.name, "unit_count": len(children)},
        )


def _sum_usage(children: Iterable[RunResult]) -> dict[str, Any]:
    totals: dict[str, Any] = {}
    for child in children:
        for key, value in child.usage.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                totals[key] = totals.get(key, 0) + value
    return totals


@dataclass(frozen=True)
class ParallelPlan:
    """Execute independent units concurrently with the same input."""

    name: str = "parallel"
    max_workers: int | None = None

    def execute(
        self,
        units: Iterable[Executable],
        input: Any = None,
        **kwargs: Any,
    ) -> RunResult:
        from concurrent.futures import ThreadPoolExecutor

        materialized = tuple(units)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            children = list(
                pool.map(lambda unit: coerce_run_result(unit.run(input, **kwargs)), materialized)
            )
        return RunResult(
            data={"results": [child.data for child in children]},
            ok=all(child.ok for child in children),
            messages=[message for child in children for message in child.messages],
            tool_events=[event for child in children for event in child.tool_events],
            raw_responses=[item for child in children for item in child.raw_responses],
            usage=_sum_usage(children),
            engine="agentic-system",
            children=children,
            meta={"execution_plan": self.name, "unit_count": len(children)},
        )



@dataclass(frozen=True)
class CompiledSystem:
    """Executable snapshot of connected units and their external plan."""

    units: tuple[Executable, ...]
    plan: ExecutionPlan = field(default_factory=SequentialPlan)
    name: str = "system"

    def run(self, input: Any = None, **kwargs: Any) -> RunResult:
        result = self.plan.execute(self.units, input, **kwargs)
        result.meta.setdefault("system", self.name)
        result.meta.setdefault("compiled", True)
        return result

    async def arun(self, input: Any = None, **kwargs: Any) -> RunResult:
        import asyncio

        return await asyncio.to_thread(self.run, input, **kwargs)

    def inspect(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "execution_plan": self.plan.name,
            "unit_count": len(self.units),
        }
__all__ = [
    "AsyncExecutable",
    "CompiledSystem",
    "CallableExecutable",
    "Executable",
    "ExecutionPlan",
    "ParallelPlan",
    "SequentialPlan",
    "coerce_run_result",
    "is_executable",
]
