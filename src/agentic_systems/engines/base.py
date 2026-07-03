"""Execution engine protocol."""

from __future__ import annotations

from typing import Any, Protocol

from agentic_systems.contracts import RunPolicy
from agentic_systems.results import RunResult


class Engine(Protocol):
    name: str

    def run(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        ...

    async def arun(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        ...
