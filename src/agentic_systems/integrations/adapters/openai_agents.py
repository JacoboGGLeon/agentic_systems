"""OpenAI Agents SDK adapter with Provider materialization."""

from __future__ import annotations

import copy
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
from ...results import RunResult, public_answer_text
from ...tools.events import ToolEvent, classify_tool_failures
from ...usage import normalize_usage
from .base import (
    FrameworkAdapter,
    attach_native_result,
    effective_max_turns,
    validate_policy_support,
)
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
            if agent.output_contract is not None:
                kwargs.setdefault("output_type", agent.output_contract)
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
        validate_policy_support(self.name, policy, mode)
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
        native_agent = _execution_agent(self.prepare(agent, engine))
        _configure_model(native_agent.model, policy, mode)
        kwargs = _runner_kwargs(agent, agent.framework_config.run_kwargs)
        _configure_native_agent(native_agent, policy)
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
        validate_policy_support(self.name, policy, mode)
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
        native_agent = _execution_agent(self.prepare(agent, engine))
        _configure_model(native_agent.model, policy, mode)
        _configure_native_agent(native_agent, policy)
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
    from openai import AsyncOpenAI

    client_options = _openai_client_options(agent)
    if agent.engine == OPENAI_RUNTIME_ENGINE:
        from agents import OpenAIResponsesModel

        metadata = getattr(agent.runtime_config, "metadata", {}) or {}
        openai_metadata = metadata.get("openai") or {}
        secret = getattr(agent.runtime_config, "api_key", None)
        api_key = (
            secret.get_secret_value()
            if isinstance(secret, SecretStr)
            else secret or os.getenv("OPENAI_API_KEY")
        )
        base_url = (
            getattr(agent.runtime_config, "endpoint", None)
            or openai_metadata.get("base_url")
            or os.getenv("OPENAI_BASE_URL")
        )
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            **client_options,
        )
        return OpenAIResponsesModel(model=agent.model, openai_client=client)
    if agent.engine in {OLLAMA_RUNTIME_ENGINE, VLLM_RUNTIME_ENGINE}:
        from agents import OpenAIChatCompletionsModel

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
        from .openai_models import ToolCallNormalizingModel

        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            **client_options,
        )
        delegate = OpenAIChatCompletionsModel(
            model=agent.model,
            openai_client=client,
        )
        available_tools = getattr(agent, "available_tools", lambda: [])()
        aliases = tool_name_aliases(available_tools)
        return ToolCallNormalizingModel(
            delegate,
            [aliases.native(tool.name) for tool in available_tools],
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


def _openai_client_options(agent: Any) -> dict[str, Any]:
    """Bind SDK retries/timeouts to the canonical scheduler contract."""

    scheduler_factory = getattr(agent, "_scheduler", None)
    if not callable(scheduler_factory):
        return {}
    scheduler = scheduler_factory()
    options: dict[str, Any] = {
        "max_retries": int(getattr(scheduler, "max_retries", 0)),
    }
    timeout_s = getattr(scheduler, "timeout_s", None)
    if timeout_s is not None:
        timeout = float(timeout_s)
        # Leave a small coordination reserve so the SDK releases its worker
        # before the outer scheduler timeout expires.
        reserve = min(1.0, timeout * 0.05)
        options["timeout"] = max(0.001, timeout - reserve)
    return options


def _configure_model(model: Any, policy: RunPolicy, mode: str) -> None:
    configure = getattr(model, "configure", None)
    if callable(configure):
        configure(policy, mode)


def _execution_agent(native_agent: Any) -> Any:
    """Create an isolated SDK Agent for one execution.

    The adapter caches the prepared native object for inspection and reuse. Per-run
    policy projection must never mutate that shared object, especially when a tool
    budget changes tool selection after the final authorized call.
    """

    if dataclasses.is_dataclass(native_agent):
        return cast(
            Any,
            dataclasses.replace(
                cast(Any, native_agent),
                tools=list(getattr(native_agent, "tools", ()) or ()),
            ),
        )
    execution_agent = copy.copy(native_agent)
    if hasattr(native_agent, "tools"):
        execution_agent.tools = list(getattr(native_agent, "tools", ()) or ())
    return execution_agent


def _configure_native_agent(native_agent: Any, policy: RunPolicy) -> None:
    """Project the shared policy into the OpenAI Agents model contract."""

    settings = getattr(native_agent, "model_settings", None)
    if settings is not None and dataclasses.is_dataclass(settings):
        has_tools = bool(getattr(native_agent, "tools", ()) or ())
        fields = {field.name for field in dataclasses.fields(settings)}
        updates: dict[str, Any] = {
            "temperature": policy.temperature,
            # OpenAI-compatible servers reject tool_choice when the request has no
            # tools. Keep the policy projection valid for completion-only agents.
            "tool_choice": policy.tool_choice if has_tools else None,
        }
        if policy.max_tokens is not None:
            updates["max_tokens"] = policy.max_tokens
        if (
            has_tools
            and policy.max_tool_calls is not None
            and "parallel_tool_calls" in fields
        ):
            updates["parallel_tool_calls"] = False
        native_agent.model_settings = dataclasses.replace(
            cast(Any, settings), **updates
        )
    _configure_tool_budget(native_agent, policy)


def _configure_tool_budget(native_agent: Any, policy: RunPolicy) -> None:
    """Prevent another SDK tool turn after the portable budget is exhausted."""

    limit = policy.max_tool_calls
    if limit is None:
        return
    if limit == 0:
        native_agent.tools = []
        _set_tool_choice(native_agent, None)
        return
    if getattr(native_agent, "tool_use_behavior", "run_llm_again") != "run_llm_again":
        return

    from agents import ToolsToFinalOutputResult

    consumed = 0

    def after_tools(_context: Any, tool_results: list[Any]) -> Any:
        nonlocal consumed
        consumed += len(tool_results)
        if consumed >= limit:
            _disable_tool_choice(native_agent)
        return ToolsToFinalOutputResult(is_final_output=False, final_output=None)

    native_agent.tool_use_behavior = after_tools


def _disable_tool_choice(native_agent: Any) -> None:
    """Allow final synthesis without invalidating prior tool protocol messages.

    Tool definitions remain attached because some provider protocols require their
    schema whenever the conversation history contains tool calls or tool results.
    The portable postcondition still fails closed if a model emits another call.
    """

    _set_tool_choice(native_agent, "none")


def _set_tool_choice(native_agent: Any, value: str | None) -> None:
    settings = getattr(native_agent, "model_settings", None)
    if settings is not None and dataclasses.is_dataclass(settings):
        native_agent.model_settings = dataclasses.replace(
            cast(Any, settings), tool_choice=value
        )


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
    rejected_tool_calls = list(getattr(bridged, "rejected_tool_calls", ()) or ())
    provider_result = getattr(bridged, "last_result", None)
    if isinstance(provider_result, RunResult):
        provider_result.meta["framework_adapter"] = "openai-agents"
        provider_result.meta["input"] = _jsonable(input_value)
        provider_result.meta["rejected_tool_calls"] = rejected_tool_calls
        return provider_result

    final_output = getattr(native_result, "final_output", "")
    text = _output_text(final_output)
    data = _output_data(final_output, text)
    raw_responses = [
        _jsonable(item) for item in getattr(native_result, "raw_responses", ())
    ]
    events = _tool_events(native_result, aliases)
    _recovered, unresolved = classify_tool_failures(events)
    failed = [ToolEvent.model_validate(item) for item in unresolved]
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
            "rejected_tool_calls": rejected_tool_calls,
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
    return normalize_usage(payload)


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
    projected = public_answer_text(value)
    if projected:
        return projected
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
