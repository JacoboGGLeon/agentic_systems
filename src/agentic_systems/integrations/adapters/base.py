"""Framework adapter protocol and shared execution helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...contracts import RunPolicy
from ...results import RunResult


class FrameworkAdapter(ABC):
    """Execute one real orchestration Framework around a selected Provider."""

    name: str
    # SDKs whose sync runner owns main-thread event-loop state opt into caller.
    # Other adapters retain interruptible worker-lane timeouts.
    sync_execution_lane: str = "worker"

    @abstractmethod
    def prepare(self, agent: Any, engine: Any) -> Any:
        """Build and return the framework-native agent without model execution."""

    @abstractmethod
    def run(
        self,
        agent: Any,
        engine: Any,
        input_value: Any,
        policy: RunPolicy,
        *,
        mode: str,
    ) -> RunResult:
        """Run synchronously through the Framework SDK."""

    @abstractmethod
    async def arun(
        self,
        agent: Any,
        engine: Any,
        input_value: Any,
        policy: RunPolicy,
        *,
        mode: str,
    ) -> RunResult:
        """Run asynchronously through the Framework SDK."""

    @staticmethod
    def native_agent(agent: Any, build: Any) -> Any:
        current = getattr(agent, "_native_agent", None)
        if current is None:
            current = build()
            agent._native_agent = current
        return current


def attach_native_result(result: RunResult, native_result: Any) -> RunResult:
    result._native_result = native_result
    return result


def effective_max_turns(policy: RunPolicy, run_kwargs: dict[str, Any]) -> int:
    requested = run_kwargs.pop("max_turns", None)
    if requested is None:
        return policy.max_turns
    value = int(requested)
    if value < 1:
        raise ValueError("Framework run_kwargs.max_turns must be >= 1.")
    return min(policy.max_turns, value)


__all__ = ["FrameworkAdapter", "attach_native_result", "effective_max_turns"]
