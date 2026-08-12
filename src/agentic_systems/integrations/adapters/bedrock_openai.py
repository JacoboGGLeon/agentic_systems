"""Bedrock Converse model for the native OpenAI Agents Runner."""

from __future__ import annotations

import ast
import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Mapping
from typing import Any

from agents import ModelResponse
from agents.models.interface import Model
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)


class BedrockOpenAIModel(Model):
    """Translate OpenAI Agents model turns to Bedrock Converse turns."""

    def __init__(self, runtime: Any, model_id: str) -> None:
        self.runtime = runtime
        self.model_id = model_id

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        system_instructions = kwargs.get("system_instructions")
        input_value = kwargs.get("input") if "input" in kwargs else args[1]
        model_settings = kwargs.get("model_settings")
        tools = kwargs.get("tools") if "tools" in kwargs else args[3]
        messages, extra_system = _bedrock_messages(input_value)
        system = ([{"text": str(system_instructions)}] if system_instructions else [])
        system.extend(extra_system)
        tool_specs = _bedrock_tools(tools or [])
        response = await asyncio.to_thread(
            self.runtime.converse,
            messages=messages,
            system=system or None,
            tools=tool_specs or None,
            tool_choice=_tool_choice(
                getattr(model_settings, "tool_choice", None),
                bool(tool_specs),
            ),
            model_id=self.model_id,
            max_tokens=getattr(model_settings, "max_tokens", None),
            temperature=getattr(model_settings, "temperature", None),
            top_p=getattr(model_settings, "top_p", None),
        )
        return _model_response(response)

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("Bedrock OpenAI Agents streaming is not implemented.")
        yield  # pragma: no cover


def _bedrock_messages(input_value: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    items = [_jsonable(item) for item in input_value] if isinstance(input_value, list) else []
    if not items:
        return [{"role": "user", "content": [{"text": _text(input_value)}]}], []

    messages: list[dict[str, Any]] = []
    system: list[dict[str, str]] = []
    index = 0
    while index < len(items):
        item = items[index]
        if not isinstance(item, Mapping):
            index += 1
            continue
        if item.get("type") == "function_call":
            calls: list[dict[str, Any]] = []
            while index < len(items) and items[index].get("type") == "function_call":
                call = items[index]
                calls.append(
                    {
                        "toolUse": {
                            "toolUseId": str(call.get("call_id") or call.get("id") or uuid.uuid4().hex),
                            "name": str(call.get("name") or ""),
                            "input": _object(call.get("arguments")),
                        }
                    }
                )
                index += 1
            messages.append({"role": "assistant", "content": calls})
            continue
        if item.get("type") == "function_call_output":
            outputs: list[dict[str, Any]] = []
            while index < len(items) and items[index].get("type") == "function_call_output":
                output = items[index]
                value = _decode(output.get("output"))
                content = {"json": value} if isinstance(value, (dict, list)) else {"text": str(value)}
                outputs.append(
                    {
                        "toolResult": {
                            "toolUseId": str(output.get("call_id") or ""),
                            "content": [content],
                        }
                    }
                )
                index += 1
            messages.append({"role": "user", "content": outputs})
            continue

        role = str(item.get("role") or "user")
        text = _content_text(item.get("content"))
        if role in {"system", "developer"}:
            if text:
                system.append({"text": text})
        elif role in {"user", "assistant"}:
            messages.append({"role": role, "content": [{"text": text}]})
        index += 1
    return messages or [{"role": "user", "content": [{"text": ""}]}], system


def _bedrock_tools(tools: list[Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for tool in tools:
        name = str(getattr(tool, "name", "") or "")
        if not name:
            continue
        schema = getattr(tool, "params_json_schema", None) or {
            "type": "object",
            "properties": {},
        }
        output.append(
            {
                "toolSpec": {
                    "name": name,
                    "description": getattr(tool, "description", None) or f"Tool {name}",
                    "inputSchema": {"json": schema},
                }
            }
        )
    return output


def _tool_choice(value: Any, has_tools: bool) -> dict[str, Any] | None:
    if not has_tools:
        return None
    if value in {"required", "any"}:
        return {"any": {}}
    if isinstance(value, str) and value not in {"", "auto", "none"}:
        return {"tool": {"name": value}}
    return {"auto": {}}


def _model_response(response: Mapping[str, Any]) -> ModelResponse:
    output: list[Any] = []
    content = response.get("output", {}).get("message", {}).get("content", [])
    for block in content:
        if not isinstance(block, Mapping):
            continue
        if "text" in block and str(block["text"]).strip():
            output.append(
                ResponseOutputMessage(
                    id=f"msg_{uuid.uuid4().hex}",
                    content=[
                        ResponseOutputText(
                            annotations=[],
                            text=str(block["text"]),
                            type="output_text",
                        )
                    ],
                    role="assistant",
                    status="completed",
                    type="message",
                )
            )
        tool_use = block.get("toolUse")
        if isinstance(tool_use, Mapping):
            output.append(
                ResponseFunctionToolCall(
                    arguments=json.dumps(tool_use.get("input") or {}, default=str),
                    call_id=str(tool_use.get("toolUseId") or uuid.uuid4().hex),
                    name=str(tool_use.get("name") or ""),
                    type="function_call",
                )
            )
    usage = response.get("usage") or {}
    return ModelResponse(
        output=output,
        usage=Usage(
            requests=1,
            input_tokens=int(usage.get("inputTokens") or 0),
            output_tokens=int(usage.get("outputTokens") or 0),
            total_tokens=int(usage.get("totalTokens") or 0),
        ),
        response_id=str(response.get("ResponseMetadata", {}).get("RequestId") or uuid.uuid4().hex),
    )


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("text") or item.get("content") or "")
            for item in content
            if isinstance(item, Mapping)
        )
    return _text(content)


def _object(value: Any) -> dict[str, Any]:
    decoded = _decode(value)
    return dict(decoded) if isinstance(decoded, Mapping) else {"input": decoded}


def _decode(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(_jsonable(value), default=str)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


__all__ = ["BedrockOpenAIModel"]
