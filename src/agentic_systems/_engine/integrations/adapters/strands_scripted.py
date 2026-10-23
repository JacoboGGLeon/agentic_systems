"""Deterministic Python model that drives the native Strands tool loop."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator, AsyncIterable, Mapping
from typing import Any

from strands.models import Model


class ScriptedStrandsModel(Model):
    """Translate a structured Python plan into native Strands tool calls."""

    def __init__(self, model_id: str = "python-runtime") -> None:
        self.config: dict[str, Any] = {
            "model_id": model_id,
            "context_window_limit": 200_000,
        }

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return dict(self.config)

    async def structured_output(
        self,
        output_model: type[Any],
        prompt: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"output": output_model.model_validate(_parse_value(prompt))}

    async def stream(
        self,
        messages: Any,
        tool_specs: list[Any] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[dict[str, Any]]:
        outputs = _tool_outputs(messages)
        structured_spec = next(
            (
                spec
                for spec in tool_specs or []
                if _is_structured_output_spec(spec)
            ),
            None,
        )
        if outputs and structured_spec is not None:
            value: Any = outputs[0] if len(outputs) == 1 else outputs
            call_id = f"python_{uuid.uuid4().hex}"
            yield {
                "contentBlockStart": {
                    "start": {
                        "toolUse": {
                            "toolUseId": call_id,
                            "name": _tool_name(structured_spec),
                        }
                    }
                }
            }
            yield {
                "contentBlockDelta": {
                    "delta": {"toolUse": {"input": json.dumps(value, default=str)}}
                }
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            yield _metadata()
            return

        yield {"messageStart": {"role": "assistant"}}
        if not outputs:
            for call in _plan_calls(messages, tool_specs or []):
                call_id = f"python_{uuid.uuid4().hex}"
                yield {
                    "contentBlockStart": {
                        "start": {
                            "toolUse": {
                                "toolUseId": call_id,
                                "name": call["tool"],
                            }
                        }
                    }
                }
                yield {
                    "contentBlockDelta": {
                        "delta": {
                            "toolUse": {
                                "input": json.dumps(call["input"], default=str)
                            }
                        }
                    }
                }
                yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            yield _metadata()
            return

        value: Any = outputs[0] if len(outputs) == 1 else outputs
        yield {"contentBlockStart": {"start": {}}}
        yield {
            "contentBlockDelta": {
                "delta": {"text": json.dumps(value, ensure_ascii=False, default=str)}
            }
        }
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield _metadata()


def _plan_calls(messages: Any, tool_specs: list[Any]) -> list[dict[str, Any]]:
    payload = _parse_value(_user_input(messages))
    names = [name for spec in tool_specs if (name := _tool_name(spec))]
    if isinstance(payload, Mapping):
        for key in ("steps", "calls"):
            if isinstance(payload.get(key), list):
                return [_normalize_call(item, names) for item in payload[key]]
        if any(key in payload for key in ("tool", "tool_name", "name")):
            return [_normalize_call(payload, names)]
        if len(names) == 1:
            return [{"tool": names[0], "input": dict(payload)}]
    if len(names) == 1:
        return [{"tool": names[0], "input": {"input": payload}}]
    return []


def _normalize_call(item: Any, names: list[str]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise TypeError("Scripted Strands tool calls must be mappings.")
    name = str(item.get("tool") or item.get("tool_name") or item.get("name") or "")
    if name not in names:
        raise KeyError(f"Unknown scripted Tool {name!r}. Available Tools: {names}.")
    payload = item.get("input", item.get("args", item.get("payload", {})))
    return {
        "tool": name,
        "input": dict(payload) if isinstance(payload, Mapping) else {"input": payload},
    }


def _tool_name(spec: Any) -> str:
    if not isinstance(spec, Mapping):
        return str(getattr(spec, "name", "") or "")
    nested = spec.get("toolSpec") if isinstance(spec.get("toolSpec"), Mapping) else spec
    return str(nested.get("name") or "")


def _is_structured_output_spec(spec: Any) -> bool:
    if not isinstance(spec, Mapping):
        return False
    nested = spec.get("toolSpec") if isinstance(spec.get("toolSpec"), Mapping) else spec
    description = str(nested.get("description") or "")
    return "StructuredOutputTool" in description


def _user_input(messages: Any) -> Any:
    if not isinstance(messages, list):
        return messages
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        blocks = message.get("content", ())
        if any(isinstance(block, Mapping) and "toolResult" in block for block in blocks):
            continue
        texts = [
            str(block.get("text") or "")
            for block in blocks
            if isinstance(block, Mapping) and "text" in block
        ]
        if texts:
            return "\n".join(texts)
    return messages


def _tool_outputs(messages: Any) -> list[Any]:
    if not isinstance(messages, list):
        return []
    turn_start = 0
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        blocks = message.get("content", ())
        has_text = any(
            isinstance(block, Mapping) and "text" in block for block in blocks
        )
        has_result = any(
            isinstance(block, Mapping) and "toolResult" in block for block in blocks
        )
        if has_text and not has_result:
            turn_start = index + 1
            break

    for message in reversed(messages[turn_start:]):
        if not isinstance(message, Mapping):
            continue
        outputs: list[Any] = []
        for block in message.get("content", ()):
            result = block.get("toolResult") if isinstance(block, Mapping) else None
            if not isinstance(result, Mapping):
                continue
            content = result.get("content") or []
            values = [
                _parse_value(item.get("json", item.get("text")))
                for item in content
                if isinstance(item, Mapping)
            ]
            outputs.append(values[0] if len(values) == 1 else values)
        if outputs:
            return outputs
    return []


def _parse_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _metadata() -> dict[str, Any]:
    return {
        "metadata": {
            "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
            "metrics": {"latencyMs": 0},
        }
    }


__all__ = ["ScriptedStrandsModel"]
