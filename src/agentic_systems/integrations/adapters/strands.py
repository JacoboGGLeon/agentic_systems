"""Strands Agents SDK adapter with Provider materialization."""

from __future__ import annotations

import inspect
import json
import os
from collections.abc import Mapping
from typing import Any, cast, get_type_hints

from ...contracts import RunPolicy
from ...engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OLLAMA_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
)
from ...protocols import AsyncRunner, SyncRunner
from ...registry import provider_capability
from ...results import RunResult
from ...tools.events import ToolEvent
from .base import FrameworkAdapter, attach_native_result, effective_max_turns
from .tools import ToolNameAliases, merge_tools, tool_name_aliases


class StrandsFrameworkAdapter(FrameworkAdapter):
    name = "strands"

    def prepare(self, agent: Any, engine: Any) -> Any:
        def build() -> Any:
            try:
                from strands import Agent as NativeAgent
            except ImportError as exc:
                raise ImportError(
                    'Strands execution requires `pip install "agentic-systems[strands]"`.'
                ) from exc

            kwargs = dict(agent.framework_config.agent_kwargs)
            kwargs.setdefault("callback_handler", None)
            if "hooks" in kwargs:
                kwargs["hooks"] = [_strands_hook(hook) for hook in kwargs["hooks"]]
            native_tools = kwargs.pop("tools", None)
            canonical_tools = agent.available_tools()
            aliases = tool_name_aliases(canonical_tools)
            converted = [
                _strands_tool(tool, aliases.native(tool.name))
                for tool in canonical_tools
            ]
            tools = merge_tools(converted, native_tools)
            return NativeAgent(
                model=_materialize_model(agent, engine),
                tools=tools,
                system_prompt=agent.instructions,
                name=agent.name,
                **kwargs,
            )

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
        if (
            isinstance(engine, SyncRunner)
            and not agent.available_tools()
            and not agent.framework_config.agent_kwargs.get("tools")
            and provider_capability(agent.engine, "model_generation").status
            == "unsupported"
        ):
            result = cast(Any, engine).run(agent, input_value, policy, mode=mode)
            result.meta["framework_adapter"] = self.name
            return result
        native_agent = self.prepare(agent, engine)
        _configure_model(native_agent.model, policy, mode)
        kwargs = _run_kwargs(agent, policy)
        aliases = tool_name_aliases(agent.available_tools())
        try:
            native_result = native_agent(
                _input_text(aliases.map_input(input_value)), **kwargs
            )
        except (TypeError, ValueError, ImportError):
            raise
        except Exception as exc:  # noqa: BLE001 - operational SDK failures normalize.
            return _failure(agent, input_value, mode, exc)
        result = _normalize_result(
            agent, native_agent, native_result, input_value, mode, aliases
        )
        return attach_native_result(result, native_result)

    async def arun(
        self,
        agent: Any,
        engine: Any,
        input_value: Any,
        policy: RunPolicy,
        *,
        mode: str,
    ) -> RunResult:
        if (
            isinstance(engine, AsyncRunner)
            and not agent.available_tools()
            and not agent.framework_config.agent_kwargs.get("tools")
            and provider_capability(agent.engine, "model_generation").status
            == "unsupported"
        ):
            result = await cast(Any, engine).arun(agent, input_value, policy, mode=mode)
            result.meta["framework_adapter"] = self.name
            return result
        native_agent = self.prepare(agent, engine)
        _configure_model(native_agent.model, policy, mode)
        kwargs = _run_kwargs(agent, policy)
        aliases = tool_name_aliases(agent.available_tools())
        try:
            native_result = await native_agent.invoke_async(
                _input_text(aliases.map_input(input_value)),
                **kwargs,
            )
        except (TypeError, ValueError, ImportError):
            raise
        except Exception as exc:  # noqa: BLE001 - operational SDK failures normalize.
            return _failure(agent, input_value, mode, exc)
        result = _normalize_result(
            agent, native_agent, native_result, input_value, mode, aliases
        )
        return attach_native_result(result, native_result)


def _materialize_model(agent: Any, engine: Any) -> Any:
    if agent.engine == BEDROCK_RUNTIME_ENGINE:
        from botocore.config import Config
        from strands.models import BedrockModel

        runtime = getattr(getattr(engine, "system", None), "_runtime", engine)
        session = getattr(runtime, "session", None)
        auth_mode = getattr(runtime, "auth_mode", None)
        # Strands rejects boto_session + region_name. The canonical runtime
        # session already owns the region and authentication chain.
        region_name = (
            None
            if session is not None
            else getattr(agent.runtime_config, "region_name", None)
        )
        return BedrockModel(
            model_id=agent.model,
            region_name=region_name,
            boto_session=session,
            streaming=bool(getattr(runtime, "streaming", False)),
            boto_client_config=(
                Config(signature_version="v4")
                if auth_mode == "aws-credential-chain"
                else None
            ),
        )
    if agent.engine in {
        OPENAI_RUNTIME_ENGINE,
        OLLAMA_RUNTIME_ENGINE,
        VLLM_RUNTIME_ENGINE,
    }:
        from strands.models.openai import OpenAIModel

        model_class = OpenAIModel
        if agent.engine == VLLM_RUNTIME_ENGINE:

            class VLLMOpenAIModel(OpenAIModel):
                """Normalize Strands requests for the vLLM OpenAI endpoint."""

                def format_request(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
                    request = super().format_request(*args, **kwargs)
                    if not request.get("tools"):
                        request.pop("tools", None)
                        request.pop("tool_choice", None)
                    return request

            model_class = VLLMOpenAIModel
        client_args: dict[str, Any] = {}
        if agent.engine == VLLM_RUNTIME_ENGINE:
            metadata = getattr(agent.runtime_config, "metadata", {}) or {}
            vllm = metadata.get("vllm") or {}
            base_url = (
                getattr(agent.runtime_config, "endpoint", None)
                or vllm.get("base_url")
                or os.getenv("VLLM_BASE_URL")
            )
            if not base_url:
                raise ValueError(
                    "vLLM requires VLLM_BASE_URL or runtime metadata vllm.base_url."
                )
            client_args.update(
                base_url=base_url,
                api_key=(
                    _runtime_api_key(agent) or os.getenv("VLLM_API_KEY") or "vllm"
                ),
            )
        elif agent.engine == OLLAMA_RUNTIME_ENGINE:
            metadata = getattr(agent.runtime_config, "metadata", {}) or {}
            ollama = metadata.get("ollama") or {}
            client_args.update(
                base_url=(
                    getattr(agent.runtime_config, "endpoint", None)
                    or ollama.get("base_url")
                    or os.getenv("OLLAMA_BASE_URL")
                    or "http://127.0.0.1:11434/v1"
                ),
                api_key=(
                    _runtime_api_key(agent) or os.getenv("OLLAMA_API_KEY") or "ollama"
                ),
            )
        else:
            endpoint = getattr(agent.runtime_config, "endpoint", None)
            api_key = _runtime_api_key(agent) or os.getenv("OPENAI_API_KEY")
            if endpoint:
                client_args["base_url"] = endpoint
            if api_key:
                client_args["api_key"] = api_key
        return model_class(model_id=agent.model, client_args=client_args or None)
    if agent.engine == PYTHON_RUNTIME_ENGINE:
        from .strands_scripted import ScriptedStrandsModel

        return ScriptedStrandsModel(agent.model or agent.engine)
    raise ValueError(f"Unsupported Provider for Strands: {agent.engine!r}.")


class _CallbackHookProvider:
    """Compatibility adapter for Strands versions that reject plain callbacks."""

    def __init__(self, callback: Any, event_type: type[Any]) -> None:
        self.callback = callback
        self.event_type = event_type

    def register_hooks(self, registry: Any, **_: Any) -> None:
        registry.add_callback(self.event_type, self.callback)


def _strands_hook(hook: Any) -> Any:
    """Preserve HookProviders and lift a typed callback into one explicitly."""

    if callable(getattr(hook, "register_hooks", None)):
        return hook
    if not callable(hook):
        raise TypeError(
            "Strands hooks must be HookProvider objects or callables with one "
            "typed event parameter."
        )
    parameters = tuple(inspect.signature(hook).parameters.values())
    if len(parameters) != 1:
        raise TypeError(
            "A Strands hook callback must declare exactly one event parameter."
        )
    try:
        annotation = get_type_hints(hook).get(parameters[0].name)
    except (NameError, TypeError):
        annotation = parameters[0].annotation
    if annotation is inspect.Signature.empty or not isinstance(annotation, type):
        raise TypeError(
            "A Strands hook callback must type its event parameter, for example "
            "AfterInvocationEvent."
        )
    return _CallbackHookProvider(hook, annotation)


def _runtime_api_key(agent: Any) -> str | None:
    value = getattr(agent.runtime_config, "api_key", None)
    reveal = getattr(value, "get_secret_value", None)
    if callable(reveal):
        return str(reveal())
    return str(value) if value is not None else None


def _strands_tool(tool: Any, native_name: str | None = None) -> Any:
    function = tool.function
    if function is None:
        raise ValueError(f"Tool {tool.name!r} has no function.")

    from strands import tool as strands_tool

    if tool.input_schema is not None:
        schema = tool.input_schema.model_json_schema()
    else:
        parameters = list(inspect.signature(function).parameters.values())
        schema = {
            "type": "object",
            "properties": {parameter.name: {} for parameter in parameters},
            "required": [
                parameter.name
                for parameter in parameters
                if parameter.default is inspect.Signature.empty
            ],
        }
    return cast(Any, strands_tool)(
        function,
        name=native_name or tool.name,
        description=tool.description or None,
        inputSchema=schema,
    )


def _configure_model(model: Any, policy: RunPolicy, mode: str) -> None:
    configure = getattr(model, "configure", None)
    if callable(configure):
        configure(policy, mode)
        return
    update_config = getattr(model, "update_config", None)
    config = getattr(model, "config", None)
    if not callable(update_config) or not isinstance(config, Mapping):
        return
    generation_config: dict[str, Any] = {"temperature": policy.temperature}
    if policy.max_tokens is not None:
        generation_config["max_tokens"] = policy.max_tokens

    # Strands model implementations expose two public configuration shapes.
    # OpenAI-compatible models keep request parameters under config["params"];
    # Bedrock and other native models validate generation parameters at the top
    # level. Passing params to a direct model is rejected by Strands and, more
    # importantly, silently leaves temperature/max_tokens unapplied.
    if "params" not in config:
        update_config(**generation_config)
        return

    params = dict(config.get("params") or {})
    tool_choice: Any = policy.tool_choice
    if isinstance(tool_choice, str) and tool_choice not in {
        "",
        "auto",
        "none",
        "required",
    }:
        tool_choice = {
            "type": "function",
            "function": {"name": tool_choice},
        }
    params.update(generation_config, tool_choice=tool_choice)
    update_config(params=params)


def _run_kwargs(agent: Any, policy: RunPolicy) -> dict[str, Any]:
    kwargs = dict(agent.framework_config.run_kwargs)
    max_turns = effective_max_turns(policy, kwargs)
    limits = dict(kwargs.pop("limits", {}) or {})
    configured = int(limits.get("turns", max_turns))
    limits["turns"] = min(configured, max_turns)
    kwargs["limits"] = limits
    return kwargs


def _normalize_result(
    agent: Any,
    native_agent: Any,
    native_result: Any,
    input_value: Any,
    mode: str,
    aliases: ToolNameAliases | None = None,
) -> RunResult:
    provider_result = getattr(native_agent.model, "last_result", None)
    if isinstance(provider_result, RunResult):
        provider_result.meta["framework_adapter"] = "strands"
        provider_result.meta["input"] = _jsonable(input_value)
        return provider_result

    structured = getattr(native_result, "structured_output", None)
    text = _input_text(structured) if structured is not None else str(native_result)
    data = _output_data(structured, text)
    messages = [_jsonable(item) for item in getattr(native_agent, "messages", ())]
    return RunResult(
        text=text,
        data=data,
        ok=True,
        messages=messages,
        tool_events=_tool_events(messages, aliases),
        raw_responses=[_jsonable(getattr(native_result, "message", {}))],
        usage=_json_dict(getattr(native_result, "metrics", {})),
        engine=agent.engine,
        model=agent.model or "",
        mode=mode,
        meta={
            "source_result_type": type(native_result).__name__,
            "framework_adapter": "strands",
            "input": _jsonable(input_value),
            "stop_reason": getattr(native_result, "stop_reason", None),
        },
    )


def _tool_events(
    messages: list[Any],
    aliases: ToolNameAliases | None = None,
) -> list[ToolEvent]:
    aliases = aliases or tool_name_aliases(())
    calls: dict[str, dict[str, Any]] = {}
    events: list[ToolEvent] = []
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        for block in message.get("content", ()):
            if not isinstance(block, Mapping):
                continue
            call = block.get("toolUse")
            if isinstance(call, Mapping):
                call_id = str(call.get("toolUseId") or "")
                calls[call_id] = {
                    "name": str(call.get("name") or ""),
                    "input": dict(call.get("input") or {}),
                }
            result = block.get("toolResult")
            if isinstance(result, Mapping):
                call_id = str(result.get("toolUseId") or "")
                original = calls.get(call_id, {})
                status = str(result.get("status") or "success")
                events.append(
                    ToolEvent(
                        id=call_id,
                        name=aliases.canonical(str(original.get("name") or "")),
                        input=dict(original.get("input") or {}),
                        output={"data": _jsonable(result.get("content"))},
                        ok=status == "success",
                        error=None if status == "success" else {"status": status},
                        meta={"source": "strands"},
                    )
                )
    return events


def _failure(agent: Any, input_value: Any, mode: str, exc: Exception) -> RunResult:
    return RunResult(
        text=str(exc),
        data={"ok": False, "error": {"code": type(exc).__name__, "message": str(exc)}},
        ok=False,
        engine=agent.engine,
        model=agent.model or "",
        mode=mode,
        meta={
            "source_result_type": type(exc).__name__,
            "framework_adapter": "strands",
            "input": _jsonable(input_value),
        },
    )


def _input_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(_jsonable(value), ensure_ascii=False, default=str)


def _output_data(value: Any, text: str) -> dict[str, Any]:
    payload = _jsonable(value)
    if isinstance(payload, dict):
        return payload
    try:
        parsed = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return {"text": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _json_dict(value: Any) -> dict[str, Any]:
    payload = _jsonable(value)
    return payload if isinstance(payload, dict) else {}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


__all__ = ["StrandsFrameworkAdapter"]
