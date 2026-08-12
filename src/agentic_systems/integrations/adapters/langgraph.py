"""Real one-node LangGraph adapter for Agentic Systems agents."""

from __future__ import annotations

from typing import Any, TypedDict

from ...contracts import RunPolicy
from ...results import RunResult
from .base import FrameworkAdapter, attach_native_result


class _FrameworkState(TypedDict, total=False):
    input: Any
    policy: RunPolicy
    mode: str
    result: RunResult


class LangGraphFrameworkAdapter(FrameworkAdapter):
    name = "langgraph"

    def prepare(self, agent: Any, engine: Any) -> Any:
        def build() -> Any:
            try:
                from langgraph.graph import END, START, StateGraph
            except ImportError as exc:
                raise ImportError(
                    'LangGraph execution requires `pip install "agentic-systems[langgraph]"`.'
                ) from exc

            def execute(state: _FrameworkState) -> _FrameworkState:
                result = engine.run(
                    agent,
                    state.get("input"),
                    state["policy"],
                    mode=state.get("mode", "default"),
                )
                return {"result": result}

            graph = StateGraph(_FrameworkState)
            graph.add_node("agent", execute)
            graph.add_edge(START, "agent")
            graph.add_edge("agent", END)
            return graph.compile()

        return self.native_agent(agent, build)

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
        state = native.invoke({"input": input_value, "policy": policy, "mode": mode})
        result = state["result"]
        result.meta["framework_adapter"] = self.name
        return attach_native_result(result, state)

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
        state = await native.ainvoke(
            {"input": input_value, "policy": policy, "mode": mode}
        )
        result = state["result"]
        result.meta["framework_adapter"] = self.name
        return attach_native_result(result, state)


__all__ = ["LangGraphFrameworkAdapter"]
