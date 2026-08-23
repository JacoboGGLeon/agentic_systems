"""OpenAI Agents SDK adapter with Provider materialization."""

from __future__ import annotations

import dataclasses
import json
import os
from collections.abc import Mapping
from typing import Any, cast

from pydantic import SecretStr

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
from .tools import (
    ToolNameAliases,
    canonical_tool_callable,
    decode_tool_output,
    merge_tools,
    tool_name_aliases,
)


class OpenAIAgentsFrameworkAdapter(FrameworkAdapter):
    name = "openai-agents"

    def prepare(self, agent: Any, engine: Any) -> Any:
        def build() -> Any:
            try:
                from agents import Agent as NativeAgent
                from agents import function_tool
            except ImportError as exc:
                raise ImportError(
                    'OpenAI Agents execution requires `pip install "agentic-systems[openai-agents]"`.'
                ) from exc

            kwargs = dict(agent.framework_config.agent_kwargs)
            native_tools = kwargs.pop("tools", None)
            canonical_tools = agent.available_tools()
            aliases = tool_name_aliases(canonical_tools)
            converted = [
                function_tool(
                    canonical_tool_callable(tool),
                    name_override=aliases.native(tool.name),
                    description_override=tool.description or None,
                    strict_mode=tool.strict,
                )
                for tool in canonical_tools
            ]
            tools = merge_tools(converted, native_tools)
            model = _materialize_model(agent, engine)
            return NativeAgent(
                name=agent.name,
                instructions=agent.instructions,
                model=model,
                tools=tools,
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
            and not any(
                agent.framework_config.agent_kwargs.get(key)
                for key in ("tools", "handoffs")
            )
            and provider_capability(agent.engine, "model_generation").status
            == "unsupported"
        ):
            result = cast(Any, engine).run(agent, input_value, policy, mode=mode)
            result.meta["framework_adapter"] = self.name
            return result
        try:
            from agents import Runner
        except ImportError as exc:
            raise ImportError(
                'OpenAI Agents execution requires `pip install "agentic-systems[openai-agents]"`.'
            ) from exc
        native_agent = self.prepare(agent, engine)
        _configure_model(native_agent.model, policy, mode)
        kwargs = _runner_kwargs(agent, agent.framework_config.run_kwargs)
        max_turns = effective_max_turns(policy, kwargs)
        aliases = tool_name_aliases(agent.available_tools())
        try:
            native_result = Runner.run_sync(
                native_agent,
                _input_text(aliases.map_input(input_value)),
                max_turns=max_turns,
                **kwargs,
            )
        except (TypeError, ValueError, ImportError):
            raise
        except Exception as exc:  # noqa: BLE001 - operational SDK failures normalize.
            return _failure(agent, input_value, mode, exc)
        result = _normalize_result(agent, native_result, input_value, mode, aliases)
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
            and not any(
                agent.framework_config.agent_kwargs.get(key)
                for key in ("tools", "handoffs")
            )
            and provider_capability(agent.engine, "model_generation").status
            == "unsupported"
        ):
            result = await cast(Any, engine).arun(agent, input_value, policy, mode=mode)
            result.meta["framework_adapter"] = self.name
            return result
        try:
            from agents import Runner
        except ImportError as exc:
            raise ImportError(
                'OpenAI Agents execution requires `pip install "agentic-systems[openai-agents]"`.'
            ) from exc
        native_agent = self.prepare(agent, engine)
        _configure_model(native_agent.model, policy, mode)
        kwargs = _runner_kwargs(agent, agent.framework_config.run_kwargs)
        max_turns = effective_max_turns(policy, kwargs)
        aliases = tool_name_aliases(agent.available_tools())
        try:
            native_result = await Runner.run(
                native_agent,
                _input_text(aliases.map_input(input_value)),
                max_turns=max_turns,
                **kwargs,
            )
        except (TypeError, ValueError, ImportError):
            raise
        except Exception as exc:  # noqa: BLE001 - operational SDK failures normalize.
            return _failure(agent, input_value, mode, exc)
        result = _normalize_result(agent, native_result, input_value, mode, aliases)
        return attach_native_result(result, native_result)


def _materialize_model(agent: Any, engine: Any) -> Any:
    if agent.engine == OPENAI_RUNTIME_ENGINE:
        return agent.model
    if agent.engine in {OLLAMA_RUNTIME_ENGINE, VLLM_RUNTIME_ENGINE}:
        from agents import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI

        metadata = getattr(agent.runtime_config, "metadata", {}) or {}
        if agent.engine == VLLM_RUNTIME_ENGINE:
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
            secret = getattr(agent.runtime_config, "api_key", None)
            api_key = (
                secret.get_secret_value()
                if isinstance(secret, SecretStr)
                else secret or os.getenv("VLLM_API_KEY") or "vllm"
            )
        else:
            ollama = metadata.get("ollama") or {}
            base_url = (
                getattr(agent.runtime_config, "endpoint", None)
                or ollama.get("base_url")
                or os.getenv("OLLAMA_BASE_URL")
                or "http://127.0.0.1:11434/v1"
            )
            secret = getattr(agent.runtime_config, "api_key", None)
            api_key = (
                secret.get_secret_value()
                if isinstance(secret, SecretStr)
                else secret or os.getenv("OLLAMA_API_KEY") or "ollama"
            )
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return OpenAIChatCompletionsModel(
            model=agent.model,
            openai_client=client,
        )
    from .openai_models import ScriptedOpenAIModel

    if agent.engine == PYTHON_RUNTIME_ENGINE:
        return ScriptedOpenAIModel()
    if agent.engine == BEDROCK_RUNTIME_ENGINE:
        from .bedrock_openai import BedrockOpenAIModel

        return BedrockOpenAIModel(
            engine.system._runtime,
            agent.model or engine.system.model,
        )
    raise ValueError(f"Unsupported Provider for OpenAI Agents: {agent.engine!r}.")


def _configure_model(model: Any, policy: RunPolicy, mode: str) -> None:
    configure = getattr(model, "configure", None)
    if callable(configure):
        configure(policy, mode)


def _runner_kwargs(agent: Any, configured: Mapping[str, Any]) -> dict[str, Any]:
    """Apply safe per-run SDK defaults without changing global tracing state."""

    kwargs = dict(configured)
    if agent.engine == OPENAI_RUNTIME_ENGINE or kwargs.get("run_config") is not None:
        return kwargs
    from agents import RunConfig

    kwargs["run_config"] = RunConfig(tracing_disabled=True)
    return kwargs


def _normalize_result(
    agent: Any,
    native_result: Any,
    input_value: Any,
    mode: str,
    aliases: ToolNameAliases | None = None,
) -> RunResult:
    bridged = getattr(getattr(native_result, "last_agent", None), "model", None)
    provider_result = getattr(bridged, "last_result", None)
    if isinstance(provider_result, RunResult):
        provider_result.meta["framework_adapter"] = "openai-agents"
        provider_result.meta["input"] = _jsonable(input_value)
        return provider_result

    final_output = getattr(native_result, "final_output", "")
    text = _output_text(final_output)
    data = _output_data(final_output, text)
    raw_responses = [
        _jsonable(item) for item in getattr(native_result, "raw_responses", ())
    ]
    events = _tool_events(native_result, aliases)
    failed = [event for event in events if not event.ok]
    if failed:
        failure_error = failed[0].error or {
            "code": "tool_execution_failed",
            "message": f"Tool {failed[0].name!r} failed.",
        }
        text = str(failure_error.get("message") or "Tool execution failed.")
        data = {"ok": False, "error": failure_error}
    return RunResult(
        text=text,
        data=data,
        ok=not failed,
        messages=[_jsonable(item) for item in native_result.to_input_list()],
        tool_events=events,
        raw_responses=raw_responses,
        usage=_usage(native_result),
        engine=agent.engine,
        model=agent.model or "",
        mode=mode,
        errors=[event.error for event in failed if event.error],
        meta={
            "source_result_type": type(native_result).__name__,
            "framework_adapter": "openai-agents",
            "input": _jsonable(input_value),
        },
    )


def _tool_events(
    native_result: Any,
    aliases: ToolNameAliases | None = None,
) -> list[ToolEvent]:
    aliases = aliases or tool_name_aliases(())
    pending: dict[str, dict[str, Any]] = {}
    events: list[ToolEvent] = []
    for item in getattr(native_result, "new_items", ()):
        raw = _jsonable(getattr(item, "raw_item", item))
        kind = type(item).__name__
        call_id = (
            str(raw.get("call_id") or raw.get("id") or "")
            if isinstance(raw, Mapping)
            else ""
        )
        if "ToolCallItem" in kind and isinstance(raw, Mapping):
            pending[call_id] = {
                "name": str(raw.get("name") or ""),
                "input": _json_object(raw.get("arguments")),
            }
        elif "ToolCallOutputItem" in kind and isinstance(raw, Mapping):
            original = pending.get(call_id, {})
            output, ok, error = decode_tool_output(_jsonable(raw.get("output")))
            events.append(
                ToolEvent(
                    id=call_id,
                    name=aliases.canonical(
                        str(original.get("name") or raw.get("name") or "")
                    ),
                    input=dict(original.get("input") or {}),
                    output={"data": _jsonable(output)},
                    ok=ok,
                    error=error,
                    meta={"source": "openai-agents"},
                )
            )
    return events


def _usage(native_result: Any) -> dict[str, Any]:
    context = getattr(native_result, "context_wrapper", None)
    usage = getattr(context, "usage", None)
    payload = _jsonable(usage)
    return payload if isinstance(payload, dict) else {}


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
            "framework_adapter": "openai-agents",
            "input": _jsonable(input_value),
        },
    )


def _input_text(value: Any) -> str:
    return (
        value
        if isinstance(value, str)
        else json.dumps(_jsonable(value), ensure_ascii=False)
    )


def _output_text(value: Any) -> str:
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
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


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {"value": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


__all__ = ["OpenAIAgentsFrameworkAdapter"]
