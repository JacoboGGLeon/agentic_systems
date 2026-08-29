"""Custom OpenAI Agents Models for non-OpenAI Agentic Systems Providers."""

from __future__ import annotations

import ast
import dataclasses
import json
import uuid
from collections.abc import AsyncIterator, Mapping
from typing import Any, cast

from agents import ModelResponse
from agents.models.interface import Model
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

from agentic_systems.tools.parsing import parse_textual_tool_call


class ToolCallNormalizingModel(Model):
    """Normalize strict textual Tool calls before the Runner owns the loop."""

    def __init__(self, delegate: Model, tool_names: list[str]) -> None:
        self.delegate = delegate
        self.tool_names = tuple(tool_names)
        self._max_tool_calls: int | None = None
        self._emitted_tool_calls = 0
        self.rejected_tool_calls: list[dict[str, Any]] = []

    def configure(self, policy: Any, mode: str) -> None:
        """Reset the execution budget for one public Agent invocation."""

        del mode
        self._max_tool_calls = getattr(policy, "max_tool_calls", None)
        self._emitted_tool_calls = 0
        self.rejected_tool_calls = []

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        args, kwargs = self._without_tools_when_exhausted(args, kwargs)
        response = await self.delegate.get_response(*args, **kwargs)
        if any(isinstance(item, ResponseFunctionToolCall) for item in response.output):
            return self._budget_response(response)
        text = ""
        for item in response.output:
            if not isinstance(item, ResponseOutputMessage):
                continue
            for block in item.content:
                if isinstance(block, ResponseOutputText):
                    text += block.text
        parsed = parse_textual_tool_call(text, self.tool_names)
        if parsed is None:
            return response
        name, arguments = parsed
        return self._budget_response(
            ModelResponse(
                output=[
                    ResponseFunctionToolCall(
                        arguments=json.dumps(arguments, ensure_ascii=False),
                        call_id=f"call_{uuid.uuid4().hex}",
                        name=name,
                        type="function_call",
                    )
                ],
                usage=response.usage,
                response_id=response.response_id,
            )
        )

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        async for item in self.delegate.stream_response(*args, **kwargs):
            yield item

    def _without_tools_when_exhausted(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        if not self._budget_exhausted():
            return args, kwargs
        values = list(args)
        updated = dict(kwargs)
        if "tools" in updated:
            updated["tools"] = []
        elif len(values) > 3:
            values[3] = []
        if "model_settings" in updated:
            updated["model_settings"] = _without_tool_choice(updated["model_settings"])
        elif len(values) > 2:
            values[2] = _without_tool_choice(values[2])
        return tuple(values), updated

    def _budget_exhausted(self) -> bool:
        return (
            isinstance(self._max_tool_calls, int)
            and self._emitted_tool_calls >= self._max_tool_calls
        )

    def _budget_response(self, response: ModelResponse) -> ModelResponse:
        calls = [
            item
            for item in response.output
            if isinstance(item, ResponseFunctionToolCall)
        ]
        if self._max_tool_calls is None:
            self._emitted_tool_calls += len(calls)
            return response
        remaining = max(0, self._max_tool_calls - self._emitted_tool_calls)
        accepted_ids = {id(item) for item in calls[:remaining]}
        rejected = calls[remaining:]
        self.rejected_tool_calls.extend(
            {
                "name": item.name,
                "provider_call_id": item.call_id,
                "reason": "max_tool_calls_exhausted",
            }
            for item in rejected
        )
        self._emitted_tool_calls += min(len(calls), remaining)
        if not rejected:
            return response
        return ModelResponse(
            output=[
                item
                for item in response.output
                if not isinstance(item, ResponseFunctionToolCall)
                or id(item) in accepted_ids
            ],
            usage=response.usage,
            response_id=response.response_id,
        )


def _without_tool_choice(settings: Any) -> Any:
    if dataclasses.is_dataclass(settings) and not isinstance(settings, type):
        return dataclasses.replace(cast(Any, settings), tool_choice=None)
    return settings


class ScriptedOpenAIModel(Model):
    """Translate deterministic Python plans into OpenAI SDK tool calls."""

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        input_value = kwargs.get("input") if "input" in kwargs else args[1]
        tools = kwargs.get("tools") if "tools" in kwargs else args[3]
        handoffs = (
            kwargs.get("handoffs")
            if "handoffs" in kwargs
            else (args[5] if len(args) > 5 else [])
        )
        items = (
            [_jsonable(item) for item in input_value]
            if isinstance(input_value, list)
            else []
        )
        outputs = [item for item in items if item.get("type") == "function_call_output"]
        if outputs:
            payload = [_decode_output(item.get("output")) for item in outputs]
            value: Any = payload[0] if len(payload) == 1 else payload
            return _text_response(json.dumps(value, ensure_ascii=False, default=str))

        calls = _plan_calls(input_value, [*(tools or []), *(handoffs or [])])
        if not calls:
            return _text_response(_input_text(input_value))
        response_items: list[Any] = [
            ResponseFunctionToolCall(
                arguments=json.dumps(call["input"], ensure_ascii=False, default=str),
                call_id=f"call_{uuid.uuid4().hex}",
                name=call["tool"],
                type="function_call",
            )
            for call in calls
        ]
        return ModelResponse(
            output=response_items,
            usage=Usage(requests=1),
            response_id=f"python_{uuid.uuid4().hex}",
        )

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("Scripted Python streaming is not implemented.")
        yield  # pragma: no cover


def _text_response(text: str) -> ModelResponse:
    output = ResponseOutputMessage(
        id=f"msg_{uuid.uuid4().hex}",
        content=[ResponseOutputText(annotations=[], text=text, type="output_text")],
        role="assistant",
        status="completed",
        type="message",
    )
    return ModelResponse(
        output=[output],
        usage=Usage(requests=1),
        response_id=f"response_{uuid.uuid4().hex}",
    )


def _plan_calls(input_value: Any, tools: list[Any]) -> list[dict[str, Any]]:
    payload = _parse_input(input_value)
    names = [
        str(getattr(tool, "name", "") or getattr(tool, "tool_name", ""))
        for tool in tools
    ]
    if isinstance(payload, Mapping):
        for key in ("steps", "calls"):
            if isinstance(payload.get(key), list):
                return [_normalize_call(item, names) for item in payload[key]]
        if any(key in payload for key in ("tool", "tool_name", "name")):
            return [_normalize_call(payload, names)]
        if len(names) == 1:
            return [{"tool": names[0], "input": dict(payload)}]
    if len(names) == 1:
        return [{"tool": names[0], "input": _single_argument(tools[0], payload)}]
    return []


def _normalize_call(item: Any, names: list[str]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise TypeError("Scripted tool calls must be mappings.")
    name = str(item.get("tool") or item.get("tool_name") or item.get("name") or "")
    if name not in names:
        raise KeyError(f"Unknown scripted tool {name!r}. Available tools: {names}.")
    payload = item.get("input", item.get("args", item.get("payload", {})))
    return {
        "tool": name,
        "input": payload if isinstance(payload, Mapping) else {"input": payload},
    }


def _single_argument(tool: Any, value: Any) -> dict[str, Any]:
    schema = (
        getattr(tool, "params_json_schema", None)
        or getattr(tool, "input_json_schema", None)
        or {}
    )
    properties = list((schema.get("properties") or {}).keys())
    return {properties[0]: value} if len(properties) == 1 else {"input": value}


def _decode_output(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value


def _parse_input(value: Any) -> Any:
    if isinstance(value, list):
        for item in reversed(value):
            raw = _jsonable(item)
            if not isinstance(raw, Mapping) or raw.get("role") != "user":
                continue
            content = raw.get("content")
            if isinstance(content, list):
                content = "".join(
                    str(block.get("text") or block.get("content") or "")
                    for block in content
                    if isinstance(block, Mapping)
                )
            if isinstance(content, str):
                value = content
                break
    text = _input_text(value)
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text


def _input_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(_jsonable(value), ensure_ascii=False, default=str)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


__all__ = ["ScriptedOpenAIModel", "ToolCallNormalizingModel"]
