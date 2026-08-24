"""Native OpenAI runtime provider.

This module uses the official ``openai`` SDK directly and does not depend on
the OpenAI Agents SDK. It executes tool loops locally through the Agentic
Systems tool registry and normalizes the response into ``RunResult``.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from hashlib import sha256
from typing import Any
from uuid import uuid4

from agentic_systems.contracts import RunPolicy
from agentic_systems.defaults import DEFAULT_OPENAI_MODEL_ID
from agentic_systems.engines.names import OPENAI_RUNTIME_ENGINE, canonical_engine_name
from agentic_systems.results import RunResult
from agentic_systems.providers.conformance import ProviderProfile, provider_profile
from agentic_systems.tools.events import ToolEvent

_INSTALL_HINT = "Install with: pip install openai"
_OPENAI_TOOL_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _openai_module() -> Any:
    try:
        import openai
    except Exception as exc:  # pragma: no cover - optional dependency path
        raise ImportError(
            f"OpenAI runtime provider requires the official openai SDK. {_INSTALL_HINT}."
        ) from exc
    return openai


def openai_environment_snapshot() -> dict[str, Any]:
    """Return non-secret OpenAI runtime configuration for diagnostics."""

    from agentic_systems.core.runtime import _load_dotenv

    _load_dotenv()
    model = os.getenv("OPENAI_MODEL")
    return {
        "base_url": os.getenv("OPENAI_BASE_URL") or None,
        "base_url_configured": bool(os.getenv("OPENAI_BASE_URL")),
        "model": model,
        "model_configured": bool(model),
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


class OpenAIRuntimeProvider:
    """Direct OpenAI chat-completions tool-loop provider."""

    name = OPENAI_RUNTIME_ENGINE

    @classmethod
    def profile(cls) -> ProviderProfile:
        return provider_profile(cls.name)

    def __init__(
        self,
        system: Any | None = None,
        *,
        client: Any | None = None,
        async_client: Any | None = None,
    ) -> None:
        self.system = system
        self._client = client
        self._async_client = async_client

    def run(
        self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default"
    ) -> RunResult:
        messages = _build_messages(agent, input)
        tool_defs = _openai_tools(self._runtime(agent), agent)
        client = self._client or _openai_module().OpenAI()
        return _run_chat_loop(
            client,
            messages,
            tool_defs,
            runtime=self._runtime(agent),
            agent=agent,
            policy=policy,
            mode=mode,
            runtime_engine=self._runtime_engine(agent),
        )

    async def arun(
        self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default"
    ) -> RunResult:
        if self._async_client is not None:
            client = self._async_client
        else:
            openai = _openai_module()
            client = openai.AsyncOpenAI()
        messages = _build_messages(agent, input)
        tool_defs = _openai_tools(self._runtime(agent), agent)
        return await _run_chat_loop_async(
            client,
            messages,
            tool_defs,
            runtime=self._runtime(agent),
            agent=agent,
            policy=policy,
            mode=mode,
            runtime_engine=self._runtime_engine(agent),
        )

    def _runtime(self, agent: Any) -> Any:
        runtime = (
            getattr(agent, "system", None)._runtime
            if getattr(agent, "system", None) is not None
            else self.system
        )
        return getattr(runtime, "_runtime", runtime)

    def _runtime_engine(self, agent: Any) -> str:
        info = getattr(agent, "info", None)
        if callable(info):
            try:
                payload = info()
            except Exception:  # noqa: BLE001
                payload = {}
            if isinstance(payload, Mapping):
                resolved = _canonical_runtime_engine(
                    payload.get("runtime_engine") or payload.get("engine")
                )
                if resolved:
                    return resolved
        return OPENAI_RUNTIME_ENGINE


def _build_messages(agent: Any, input: Any) -> list[dict[str, Any]]:
    messages = []
    instructions = str(getattr(agent, "instructions", "") or "").strip()
    if instructions:
        messages.append({"role": "system", "content": instructions})
    messages.append({"role": "user", "content": _input_to_prompt(input)})
    return messages


def _openai_tools(runtime: Any, agent: Any) -> list[dict[str, Any]]:
    tool_specs = (
        list(getattr(runtime, "tools", []) or []) if runtime is not None else []
    )
    specs = {spec.name: spec for spec in tool_specs}
    tool_names = list(getattr(agent, "tools", ()) or [])
    if tool_names:
        tool_names = [getattr(tool, "name", tool) for tool in tool_names]
    if not tool_names:
        tool_names = [spec.name for spec in tool_specs]
    if not tool_names and hasattr(agent, "available_tools"):
        tool_names = [
            tool.name for tool in agent.available_tools() if hasattr(tool, "name")
        ]
    if not specs and hasattr(agent, "available_tools"):
        for tool in agent.available_tools():
            schema = getattr(tool, "input_schema", None)
            description = (
                getattr(tool, "description", "")
                or getattr(tool, "__doc__", "")
                or f"Tool {tool.name}"
            )
            if schema is not None and hasattr(schema, "model_json_schema"):
                input_schema = schema.model_json_schema()
            elif schema is not None and isinstance(schema, Mapping):
                input_schema = dict(schema)
            else:
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True,
                }
            specs[tool.name] = type(
                "_Spec",
                (),
                {
                    "name": tool.name,
                    "description": description,
                    "input_schema": input_schema,
                },
            )()
    defs: list[dict[str, Any]] = []
    provider_names: set[str] = set()
    for name in tool_names:
        spec = specs.get(name)
        if spec is None:
            continue
        provider_name = _provider_tool_name(spec.name)
        if provider_name in provider_names:
            raise ValueError(
                "Tool names are not unique after OpenAI-compatible normalization: "
                f"{provider_name!r}."
            )
        provider_names.add(provider_name)
        defs.append(
            {
                "type": "function",
                "function": {
                    "name": provider_name,
                    "description": spec.description,
                    "parameters": spec.input_schema,
                },
            }
        )
    return defs


def _run_chat_loop(
    client: Any,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    runtime: Any,
    agent: Any,
    policy: RunPolicy,
    mode: str,
    runtime_engine: str,
) -> RunResult:
    tool_events: list[ToolEvent] = []
    ok = True
    turns = 0
    max_turns = policy.max_turns or 8
    while True:
        turns += 1
        if turns > max_turns:
            result = _failure(
                "OpenAIRuntimeProvider exceeded max_turns.",
                agent,
                mode,
                "max_turns_exceeded",
                meta={"turns": turns, "runtime_engine": runtime_engine},
            )
            result.engine = runtime_engine
            result.tool_events = list(tool_events)
            return result
        response = client.chat.completions.create(
            model=getattr(agent, "model", None)
            or getattr(getattr(agent, "system", None), "model", None)
            or DEFAULT_OPENAI_MODEL_ID,
            messages=messages,
            tools=tools or None,
            tool_choice=_tool_choice(policy.tool_choice, tools) if tools else None,
            temperature=policy.temperature,
            max_tokens=policy.max_tokens,
        )
        choice = response.choices[0]
        message = choice.message
        assistant_content = getattr(message, "content", None) or ""
        tool_calls = list(getattr(message, "tool_calls", None) or [])
        if assistant_content:
            messages.append({"role": "assistant", "content": assistant_content})
        if not tool_calls:
            usage = _usage_from_response(response)
            return _finalize_run_result(
                assistant_content,
                tool_events,
                ok,
                usage,
                agent=agent,
                mode=mode,
                runtime_engine=runtime_engine,
                source="openai.chat.completions",
            )
        messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [_tool_call_dict(tc) for tc in tool_calls],
            }
        )
        for tc in tool_calls:
            name = _canonical_tool_name(runtime, agent, tc.function.name)
            args = _json_loads(getattr(tc.function, "arguments", "") or "{}")
            result = _execute_tool(
                runtime,
                agent,
                name,
                args,
                provider_call_id=getattr(tc, "id", None),
            )
            tool_events.append(result["event"])
            ok = ok and result["event"].ok
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result["envelope"], ensure_ascii=False),
                }
            )
            if not result["event"].ok and not policy.repair:
                usage = _usage_from_response(response)
                return _finalize_run_result(
                    _tool_result_text(result["envelope"]),
                    tool_events,
                    False,
                    usage,
                    agent=agent,
                    mode=mode,
                    runtime_engine=runtime_engine,
                    source="openai.chat.completions",
                )
            if _required_tools_satisfied(agent, tool_events):
                return _finalize_run_result(
                    _tool_result_text(result["envelope"]),
                    tool_events,
                    ok,
                    _usage_from_response(response),
                    agent=agent,
                    mode=mode,
                    runtime_engine=runtime_engine,
                    source="openai.chat.completions",
                )


async def _run_chat_loop_async(
    client: Any,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    runtime: Any,
    agent: Any,
    policy: RunPolicy,
    mode: str,
    runtime_engine: str,
) -> RunResult:
    tool_events: list[ToolEvent] = []
    ok = True
    turns = 0
    max_turns = policy.max_turns or 8
    while True:
        turns += 1
        if turns > max_turns:
            result = _failure(
                "OpenAIRuntimeProvider exceeded max_turns.",
                agent,
                mode,
                "max_turns_exceeded",
                meta={"turns": turns, "runtime_engine": runtime_engine},
            )
            result.engine = runtime_engine
            result.tool_events = list(tool_events)
            return result
        response = await client.chat.completions.create(
            model=getattr(agent, "model", None)
            or getattr(getattr(agent, "system", None), "model", None)
            or DEFAULT_OPENAI_MODEL_ID,
            messages=messages,
            tools=tools or None,
            tool_choice=_tool_choice(policy.tool_choice, tools) if tools else None,
            temperature=policy.temperature,
            max_tokens=policy.max_tokens,
        )
        choice = response.choices[0]
        message = choice.message
        assistant_content = getattr(message, "content", None) or ""
        tool_calls = list(getattr(message, "tool_calls", None) or [])
        if assistant_content:
            messages.append({"role": "assistant", "content": assistant_content})
        if not tool_calls:
            usage = _usage_from_response(response)
            return _finalize_run_result(
                assistant_content,
                tool_events,
                ok,
                usage,
                agent=agent,
                mode=mode,
                runtime_engine=runtime_engine,
                source="openai.chat.completions",
            )
        messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [_tool_call_dict(tc) for tc in tool_calls],
            }
        )
        for tc in tool_calls:
            name = _canonical_tool_name(runtime, agent, tc.function.name)
            args = _json_loads(getattr(tc.function, "arguments", "") or "{}")
            result = _execute_tool(
                runtime,
                agent,
                name,
                args,
                provider_call_id=getattr(tc, "id", None),
            )
            tool_events.append(result["event"])
            ok = ok and result["event"].ok
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result["envelope"], ensure_ascii=False),
                }
            )
            if not result["event"].ok and not policy.repair:
                usage = _usage_from_response(response)
                return _finalize_run_result(
                    _tool_result_text(result["envelope"]),
                    tool_events,
                    False,
                    usage,
                    agent=agent,
                    mode=mode,
                    runtime_engine=runtime_engine,
                    source="openai.chat.completions",
                )
            if _required_tools_satisfied(agent, tool_events):
                return _finalize_run_result(
                    _tool_result_text(result["envelope"]),
                    tool_events,
                    ok,
                    _usage_from_response(response),
                    agent=agent,
                    mode=mode,
                    runtime_engine=runtime_engine,
                    source="openai.chat.completions",
                )


def _execute_tool(
    runtime: Any,
    agent: Any,
    name: str,
    args: dict[str, Any],
    *,
    provider_call_id: str | None = None,
) -> dict[str, Any]:
    effective_runtime = getattr(runtime, "_runtime", runtime)
    envelope = (
        effective_runtime.execute_tool(name, args)
        if effective_runtime is not None
        else {"error": {"message": f"missing runtime for {name}"}}
    )
    event_id = f"tool-{uuid4().hex}"
    if hasattr(envelope, "model_dump"):
        payload = envelope.model_dump(mode="json")
        event_meta = dict(payload.get("meta") or {})
        if provider_call_id:
            event_meta["provider_tool_call_id"] = provider_call_id
        event = ToolEvent(
            id=event_id,
            name=name,
            input=args,
            output=payload.get("data") or {},
            ok=payload.get("ok", True),
            error=None if payload.get("ok", True) else payload.get("data"),
            meta=event_meta,
        )
        return {"envelope": payload, "event": event}
    event_meta = {"provider_tool_call_id": provider_call_id} if provider_call_id else {}
    event = ToolEvent(
        id=event_id,
        name=name,
        input=args,
        output=envelope if isinstance(envelope, dict) else {"value": envelope},
        ok=True,
        error=None,
        meta=event_meta,
    )
    return {"envelope": envelope, "event": event}


def _framework_meta(agent: Any) -> dict[str, Any]:
    requested = getattr(agent, "framework", None)
    return {
        "framework": requested,
        "framework_requested": requested,
        "framework_adapter": None,
    }


def _finalize_run_result(
    text: str,
    tool_events: list[ToolEvent],
    ok: bool,
    usage: dict[str, Any],
    *,
    agent: Any,
    mode: str,
    runtime_engine: str,
    source: str,
) -> RunResult:
    if ok and not str(text or "").strip():
        result = _failure(
            "Provider returned an empty model output.",
            agent,
            mode,
            "empty_model_output",
            meta={
                "source_result_type": source,
                "runtime_engine": runtime_engine,
            },
        )
        result.engine = runtime_engine
        result.tool_events = tool_events
        result.usage = usage
        return result
    result = RunResult(
        text=text,
        data={"final_output": text} if text else {},
        ok=ok,
        tool_events=tool_events,
        usage=usage,
        engine=runtime_engine,
        model=getattr(agent, "model", None) or DEFAULT_OPENAI_MODEL_ID,
        mode=mode,
        meta={
            "source_result_type": source,
            "runtime_engine": runtime_engine,
            "execution_engine": OPENAI_RUNTIME_ENGINE,
            **_framework_meta(agent),
        },
    )
    contract = getattr(agent, "contract", None)
    if contract is not None and hasattr(result, "validate"):
        validation = result.validate(contract)
        result.apply_validation(validation)
    return result


def _failure(
    message: str, agent: Any, mode: str, code: str, meta: dict[str, Any] | None = None
) -> RunResult:
    return RunResult(
        text=message,
        data={"ok": False, "error": {"code": code, "message": message}},
        ok=False,
        engine=OPENAI_RUNTIME_ENGINE,
        model=getattr(agent, "model", None) or DEFAULT_OPENAI_MODEL_ID,
        mode=mode,
        meta={
            "execution_engine": OPENAI_RUNTIME_ENGINE,
            **_framework_meta(agent),
            **(meta or {}),
        },
    )


def _usage_from_response(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    payload = {}
    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "completion_tokens",
        "prompt_tokens",
    ):
        value = getattr(usage, key, None)
        if value is not None:
            payload[key] = value
    return payload


def _required_tools_satisfied(agent: Any, tool_events: list[ToolEvent]) -> bool:
    contract = getattr(agent, "contract", None)
    completion = getattr(contract, "completion", None)
    if completion not in {
        "when_contract_satisfied",
        "when_required_tools_satisfied",
    }:
        return False
    required = set(getattr(contract, "must_call", ()) or ())
    successful = {event.name for event in tool_events if event.ok}
    return bool(required) and required.issubset(successful)


def _tool_choice(
    choice: Any,
    tools: list[dict[str, Any]] | None = None,
) -> Any:
    if choice is None:
        return "auto"
    if not isinstance(choice, str):
        return "auto"
    if choice == "auto":
        return "auto"
    if choice in {"required", "any"}:
        if tools and len(tools) == 1:
            function = tools[0].get("function")
            if isinstance(function, Mapping):
                name = function.get("name")
                if isinstance(name, str) and name:
                    return {
                        "type": "function",
                        "function": {"name": name},
                    }
        return "required"
    return {
        "type": "function",
        "function": {"name": _provider_tool_name(choice)},
    }


def _provider_tool_name(name: str) -> str:
    """Return a stable OpenAI-compatible alias without changing public identity."""

    canonical = str(name)
    if _OPENAI_TOOL_NAME.fullmatch(canonical):
        return canonical
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", canonical).strip("_-") or "tool"
    digest = sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"as_{slug[:44]}_{digest}"


def _canonical_tool_name(runtime: Any, agent: Any, provider_name: str) -> str:
    """Resolve a provider alias back to the registered canonical tool name."""

    candidates: list[str] = []
    effective_runtime = getattr(runtime, "_runtime", runtime)
    for spec in list(getattr(effective_runtime, "tools", []) or []):
        name = getattr(spec, "name", None)
        if name:
            candidates.append(str(name))
    if hasattr(agent, "available_tools"):
        for tool in agent.available_tools():
            name = getattr(tool, "name", None)
            if name and str(name) not in candidates:
                candidates.append(str(name))
    matches = [
        name for name in candidates if _provider_tool_name(name) == provider_name
    ]
    if len(matches) > 1:
        raise ValueError(
            "Ambiguous OpenAI-compatible tool alias "
            f"{provider_name!r}: {sorted(matches)!r}."
        )
    return matches[0] if matches else provider_name


def _tool_call_dict(tc: Any) -> dict[str, Any]:
    return {
        "id": getattr(tc, "id", None),
        "type": "function",
        "function": {
            "name": getattr(getattr(tc, "function", None), "name", None),
            "arguments": getattr(getattr(tc, "function", None), "arguments", "{}"),
        },
    }


def _json_loads(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except Exception:
        return {"input": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _tool_result_text(envelope: Any) -> str:
    if hasattr(envelope, "model_dump"):
        envelope = envelope.model_dump(mode="json")
    if isinstance(envelope, Mapping):
        data = envelope.get("data")
        if isinstance(data, Mapping):
            for key in ("summary", "text", "message", "error"):
                if data.get(key):
                    return str(data[key])
        return json.dumps(envelope, ensure_ascii=False)
    return str(envelope)


def _canonical_runtime_engine(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        resolved = canonical_engine_name(str(value))
    except Exception:  # noqa: BLE001
        return None
    if resolved == OPENAI_RUNTIME_ENGINE:
        return None
    return resolved


def _input_to_prompt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "model_dump_json"):
        try:
            return value.model_dump_json(indent=2)
        except TypeError:
            return value.model_dump_json()
    try:
        return json.dumps(_jsonable(value), ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


__all__ = ["OpenAIRuntimeProvider", "openai_environment_snapshot", "_input_to_prompt"]
