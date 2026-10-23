"""Agentic Systems native Framework adapter."""

from __future__ import annotations

import asyncio
from typing import Any

from ...contracts import RunPolicy
from ...results import RunResult
from ..config import NATIVE_FRAMEWORK
from .base import FrameworkAdapter, attach_native_result


class NativeFrameworkAdapter(FrameworkAdapter):
    name = NATIVE_FRAMEWORK

    def prepare(self, agent: Any, engine: Any) -> Any:
        return self.native_agent(agent, lambda: engine)

    def run(
        self,
        agent: Any,
        engine: Any,
        input_value: Any,
        policy: RunPolicy,
        *,
        mode: str,
    ) -> RunResult:
        native = self.prepare(agent, engine)
        result = native.run(agent, input_value, policy, mode=mode)
        return attach_native_result(result, result)

    async def arun(
        self,
        agent: Any,
        engine: Any,
        input_value: Any,
        policy: RunPolicy,
        *,
        mode: str,
    ) -> RunResult:
        native = self.prepare(agent, engine)
        if hasattr(native, "arun"):
            result = await native.arun(agent, input_value, policy, mode=mode)
        else:
            result = await asyncio.to_thread(
                native.run,
                agent,
                input_value,
                policy,
                mode=mode,
            )
        return attach_native_result(result, result)


__all__ = ["NativeFrameworkAdapter"]
