"""Deterministic local Python provider.

This is the canonical home for the local tool-execution path.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable, Mapping
from typing import Any

from agentic_systems.contracts import RunPolicy
from agentic_systems.engines.names import PYTHON_RUNTIME_ENGINE
from agentic_systems.results import RunResult
from agentic_systems.providers.conformance import ProviderProfile, provider_profile
from agentic_systems.tools import Tool
from agentic_systems.tools.events import ToolEvent


class PythonRuntimeProvider:
    """Local deterministic provider for tool-backed agents."""

    name = PYTHON_RUNTIME_ENGINE

    @classmethod
    def profile(cls) -> ProviderProfile:
        return provider_profile(cls.name)

    def __init__(self, system: Any | None = None) -> None:
        self.system = system

    def run(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        tools = _tool_registry(agent)
        if not tools:
            return _failure(
                message="PythonRuntimeProvider needs at least one concrete Tool on the agent.",
                agent=agent,
                mode=mode,
                code="missing_tools",
                meta={"agent_tools": list(getattr(agent, "tools", ()) or [])},
            )

        try:
            pipeline = _parse_pipeline(input, tools)
            if pipeline is not None:
                names, state = pipeline
                if policy.max_tool_calls is not None and len(names) > policy.max_tool_calls:
                    return _failure(
                        message=f"PythonRuntimeProvider planned {len(names)} tool calls, above max_tool_calls={policy.max_tool_calls}.",
                        agent=agent,
                        mode=mode,
                        code="max_tool_calls_exceeded",
                        meta={"planned_tool_calls": len(names), "max_tool_calls": policy.max_tool_calls},
                    )
                return _run_pipeline(agent, tools, names, state, policy, mode=mode)
            calls = _parse_plan(input, tools)
        except Exception as exc:  # noqa: BLE001
            return _failure(
                message=str(exc),
                agent=agent,
                mode=mode,
                code=type(exc).__name__,
                meta={"available_tools": sorted(tools)},
            )

        if policy.max_tool_calls is not None and len(calls) > policy.max_tool_calls:
            return _failure(
                message=f"PythonRuntimeProvider planned {len(calls)} tool calls, above max_tool_calls={policy.max_tool_calls}.",
                agent=agent,
                mode=mode,
                code="max_tool_calls_exceeded",
                meta={"planned_tool_calls": len(calls), "max_tool_calls": policy.max_tool_calls},
            )

        return _run_calls(agent, tools, calls, policy, mode=mode)

    async def arun(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        return await asyncio.to_thread(self.run, agent, input, policy, mode=mode)


class PythonRuntimeEngine(PythonRuntimeProvider):
    """Execution engine for the deterministic Python Provider."""


def _tool_registry(agent: Any) -> dict[str, Tool]:
    if not hasattr(agent, "available_tools"):
        return {}
    tools = agent.available_tools()
    return {tool.name: tool for tool in tools if isinstance(tool, Tool)}


def _run_calls(agent: Any, tools: Mapping[str, Tool], calls: list[dict[str, Any]], policy: RunPolicy, *, mode: str) -> RunResult:
    outputs: list[dict[str, Any]] = []
    events: list[ToolEvent] = []
    ok = True
    for index, call in enumerate(calls):
        tool = tools[call["tool"]]
        result = tool.run(call.get("input"), context={"engine": PythonRuntimeProvider.name, "agent": getattr(agent, "name", ""), "index": index})
        events.extend(result.tool_events)
        output_data = result.data if isinstance(result.data, dict) else {"value": result.data}
        outputs.append(
            {
                "index": index,
                "tool": tool.name,
                "input": _json_like(call.get("input")),
                "ok": result.ok,
                "output": output_data,
            }
        )
        ok = ok and bool(result.ok)
        if not result.ok and not policy.repair:
            break

    data = _result_data(outputs, ok=ok)
    text = _result_text(data, outputs)
    return RunResult(
        text=text,
        data=data,
        ok=ok,
        tool_events=events,
        engine=PythonRuntimeProvider.name,
        model=getattr(agent, "model", None) or PYTHON_RUNTIME_ENGINE,
        mode=mode,
        meta={
            "source_result_type": PythonRuntimeProvider.__name__,
            "agent_name": getattr(agent, "name", ""),
            "tool_count": len(tools),
            "planned_tool_calls": len(calls),
        },
    )


def _run_pipeline(
    agent: Any,
    tools: Mapping[str, Tool],
    names: list[str],
    state: Any,
    policy: RunPolicy,
    *,
    mode: str,
) -> RunResult:
    outputs: list[dict[str, Any]] = []
    events: list[ToolEvent] = []
    ok = True
    current = state
    for index, name in enumerate(names):
        tool = tools[name]
        input_snapshot = _json_like(current)
        result = tool.run(current, context={"engine": PythonRuntimeProvider.name, "agent": getattr(agent, "name", ""), "index": index})
        events.extend(result.tool_events)
        output_data = result.data if isinstance(result.data, dict) else {"value": result.data}
        outputs.append({"index": index, "tool": name, "input": input_snapshot, "ok": result.ok, "output": output_data})
        ok = ok and bool(result.ok)
        current = output_data
        if not result.ok and not policy.repair:
            break

    data = _result_data(outputs, ok=ok)
    text = _result_text(data, outputs)
    return RunResult(
        text=text,
        data=data,
        ok=ok,
        tool_events=events,
        engine=PythonRuntimeProvider.name,
        model=getattr(agent, "model", None) or PYTHON_RUNTIME_ENGINE,
        mode=mode,
        meta={
            "source_result_type": PythonRuntimeProvider.__name__,
            "agent_name": getattr(agent, "name", ""),
            "tool_count": len(tools),
            "planned_tool_calls": len(outputs),
            "execution_style": "state_pipeline",
        },
    )


def _parse_pipeline(input_value: Any, tools: Mapping[str, Tool]) -> tuple[list[str], Any] | None:
    if not isinstance(input_value, Mapping):
        return None

    if "pipeline" in input_value:
        raw = input_value.get("pipeline")
        if isinstance(raw, Mapping):
            names = raw.get("tools") or raw.get("order") or raw.get("names")
            state = raw.get("state", input_value.get("state", {}))
        else:
            names = raw
            state = input_value.get("state", {})
        return _normalize_pipeline(names, state, tools)

    raw_tools = input_value.get("tools")
    if "state" in input_value and isinstance(raw_tools, Iterable) and not isinstance(raw_tools, (str, bytes, Mapping)):
        raw_list = list(raw_tools)
        if all(isinstance(item, str) for item in raw_list):
            return _normalize_pipeline(raw_list, input_value.get("state"), tools)

    return None


def _normalize_pipeline(names: Any, state: Any, tools: Mapping[str, Tool]) -> tuple[list[str], Any]:
    if not isinstance(names, Iterable) or isinstance(names, (str, bytes, Mapping)):
        raise TypeError("Pipeline tools must be a list of tool names.")
    normalized = [str(name) for name in names]
    missing = [name for name in normalized if name not in tools]
    if missing:
        raise KeyError(f"Unknown pipeline tools {missing!r}. Available tools: {sorted(tools)}")
    return normalized, state


def _parse_plan(input_value: Any, tools: Mapping[str, Tool]) -> list[dict[str, Any]]:
    if isinstance(input_value, str):
        input_value = input_value.strip()
        if not input_value:
            raise ValueError("PythonRuntimeProvider received an empty string. Pass a structured tool plan or a direct payload for one tool.")
        try:
            input_value = json.loads(input_value)
        except json.JSONDecodeError as exc:
            if len(tools) == 1:
                tool_name = next(iter(tools))
                return [{"tool": tool_name, "input": input_value}]
            raise ValueError(
                "PythonRuntimeProvider is deterministic and does not parse natural language plans. "
                "Pass {'tool': '<name>', 'input': {...}} or {'steps': [...]} for local execution."
            ) from exc

    if isinstance(input_value, Mapping):
        for key in ("steps", "tools", "calls"):
            value = input_value.get(key)
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
                return [_normalize_call(item, tools) for item in value]
        if any(key in input_value for key in ("tool", "tool_name", "name")):
            return [_normalize_call(input_value, tools)]
        if len(tools) == 1:
            tool_name = next(iter(tools))
            return [{"tool": tool_name, "input": dict(input_value)}]
        raise ValueError(
            "PythonRuntimeProvider needs a tool name when the agent exposes multiple tools. "
            "Use {'tool': '<name>', 'input': {...}} or {'steps': [...]}",
        )

    if isinstance(input_value, Iterable) and not isinstance(input_value, (str, bytes)):
        return [_normalize_call(item, tools) for item in input_value]

    if len(tools) == 1:
        tool_name = next(iter(tools))
        return [{"tool": tool_name, "input": input_value}]

    raise ValueError("Unsupported PythonRuntimeProvider input. Pass a dict plan, list of plans, JSON string, or single-tool payload.")


def _normalize_call(item: Any, tools: Mapping[str, Tool]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise TypeError(f"Tool call must be a mapping, got {type(item).__name__}.")
    tool_name = item.get("tool") or item.get("tool_name") or item.get("name")
    if not tool_name:
        raise ValueError("Tool call is missing 'tool'.")
    tool_name = str(tool_name)
    if tool_name not in tools:
        raise KeyError(f"Unknown tool '{tool_name}'. Available tools: {sorted(tools)}")
    payload = item.get("input", item.get("args", item.get("payload", {})))
    return {"tool": tool_name, "input": payload}


def _result_data(outputs: list[dict[str, Any]], *, ok: bool) -> dict[str, Any]:
    if len(outputs) == 1:
        output = outputs[0]
        data = dict(output.get("output") or {})
        data.setdefault("ok", output.get("ok", ok))
        data.setdefault("tool", output.get("tool"))
        return data
    last = outputs[-1]["output"] if outputs else {}
    data = {"ok": ok, "steps": outputs, "last": last}
    if isinstance(last, dict):
        data["fields"] = last
    return data


def _summary_from_output_payload(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return ""
    for key in ("summary", "text", "message", "error"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _result_text(data: dict[str, Any], outputs: list[dict[str, Any]]) -> str:
    if len(outputs) == 1:
        output = outputs[0]
        payload = output.get("output", {})
        summary = _summary_from_output_payload(payload)
        if summary:
            return summary
        return f"{output['tool']} -> {json.dumps(payload, ensure_ascii=False)}"

    summaries = []
    for output in outputs:
        summary = _summary_from_output_payload(output.get("output", {}))
        if summary:
            summaries.append(f"{output['tool']}: {summary}")
    if summaries:
        return "\n".join(summaries)
    return json.dumps(data, ensure_ascii=False)


def _failure(*, message: str, agent: Any, mode: str, code: str, meta: dict[str, Any] | None = None) -> RunResult:
    return RunResult(
        text=message,
        data={"ok": False, "error": {"code": code, "message": message}},
        ok=False,
        engine=PythonRuntimeProvider.name,
        model=getattr(agent, "model", None) or PYTHON_RUNTIME_ENGINE,
        mode=mode,
        meta={"source_result_type": PythonRuntimeProvider.__name__, **(meta or {})},
    )


def _json_like(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _json_like(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_like(item) for item in value]
    return value


__all__ = ["PythonRuntimeEngine", "PythonRuntimeProvider"]
