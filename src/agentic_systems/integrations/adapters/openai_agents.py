"""OpenAI Agents SDK adapter with Provider materialization."""

from __future__ import annotations

import copy
import dataclasses
import json
import os
from collections.abc import Mapping
from typing import Any, cast
from uuid import uuid4

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
from ...usage import merge_usage, normalize_usage
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
    _TOOL_RESULT_MARKER,
)


def _sdk_tool_failure(_context: Any, error: Exception) -> str:
    """Preserve SDK validation failures without guessing from message text."""
    return json.dumps(
        {
            _TOOL_RESULT_MARKER: {
                "ok": False,
                "data": None,
                "error": {"code": type(error).__name__, "message": str(error)},
            }
        }
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
                    failure_error_function=_sdk_tool_failure,
                )
                for tool in canonical_tools
            ]
            tools = merge_tools(converted, native_tools)
            model = _materialize_model(agent, engine)
            native_agent = NativeAgent(
                name=agent.name,
                instructions=agent.instructions,
                model=model,
                tools=tools,
                **kwargs,
            )
            # Native SDK handoffs invoke this prepared object directly, without
            # passing through run()/arun(). Preserve its declared output bound.
            declared_policy = getattr(agent, "policy", None)
            if isinstance(declared_policy, Mapping):
                declared_policy = RunPolicy.model_validate(declared_policy)
            if declared_policy is not None and declared_policy.max_tokens is not None:
                native_agent.model_settings = dataclasses.replace(
                    native_agent.model_settings, max_tokens=declared_policy.max_tokens
                )
            return native_agent

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
        max_turns = effective_max_turns(policy, kwargs)
        aliases = tool_name_aliases(agent.available_tools())
        split = _uses_structured_tool_phases(native_agent, policy)
        if split and max_turns < 2:
            return _phase_budget_failure(agent, input_value, mode, max_turns)
        action_agent = (
            _phase_agent(
                native_agent,
                output_type=None,
                output_guardrails=[],
            )
            if split
            else native_agent
        )
        _configure_native_agent(action_agent, policy)
        observed = _observe_tools(action_agent, aliases)
        action_result: Any | None = None
        action_normalized: RunResult | None = None
        action_turns = 0
        try:
            action_result = Runner.run_sync(
                action_agent,
                _input_text(aliases.map_input(input_value)),
                max_turns=max_turns - 1 if split else max_turns,
                **kwargs,
            )
            if split:
                action_turns = _native_turn_count(
                    action_result,
                    conservative_default=max_turns - 1,
                )
                action_normalized = _normalize_result(
                    agent,
                    action_result,
                    input_value,
                    mode,
                    aliases,
                )
                native_result = _run_structured_synthesis_sync(
                    Runner,
                    native_agent,
                    action_result,
                    policy,
                    max_turns=max_turns,
                    kwargs=kwargs,
                )
            else:
                native_result = action_result
        except (TypeError, ValueError, ImportError):
            raise
        except Exception as exc:  # noqa: BLE001 - operational SDK failures normalize.
            result = _failure(agent, input_value, mode, exc)
            result = _preserve_failed_action(
                action_normalized,
                result,
                observed,
            )
            if split:
                result.meta["structured_execution"] = {
                    "strategy": "tools_then_output",
                    "failed_phase": "action_or_synthesis",
                }
            return result
        result = _normalize_result(agent, native_result, input_value, mode, aliases)
        if split:
            result = _merge_structured_phases(
                cast(RunResult, action_normalized),
                action_turns,
                result,
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
        kwargs = _runner_kwargs(agent, agent.framework_config.run_kwargs)
        max_turns = effective_max_turns(policy, kwargs)
        aliases = tool_name_aliases(agent.available_tools())
        split = _uses_structured_tool_phases(native_agent, policy)
        if split and max_turns < 2:
            return _phase_budget_failure(agent, input_value, mode, max_turns)
        action_agent = (
            _phase_agent(
                native_agent,
                output_type=None,
                output_guardrails=[],
            )
            if split
            else native_agent
        )
        _configure_native_agent(action_agent, policy)
        observed = _observe_tools(action_agent, aliases)
        action_result: Any | None = None
        action_normalized: RunResult | None = None
        action_turns = 0
        try:
            action_result = await Runner.run(
                action_agent,
                _input_text(aliases.map_input(input_value)),
                max_turns=max_turns - 1 if split else max_turns,
                **kwargs,
            )
            if split:
                action_turns = _native_turn_count(
                    action_result,
                    conservative_default=max_turns - 1,
                )
                action_normalized = _normalize_result(
                    agent,
                    action_result,
                    input_value,
                    mode,
                    aliases,
                )
                native_result = await _run_structured_synthesis_async(
                    Runner,
                    native_agent,
                    action_result,
                    policy,
                    max_turns=max_turns,
                    kwargs=kwargs,
                )
            else:
                native_result = action_result
        except (TypeError, ValueError, ImportError):
            raise
        except Exception as exc:  # noqa: BLE001 - operational SDK failures normalize.
            result = _failure(agent, input_value, mode, exc)
            result = _preserve_failed_action(
                action_normalized,
                result,
                observed,
            )
            if split:
                result.meta["structured_execution"] = {
                    "strategy": "tools_then_output",
                    "failed_phase": "action_or_synthesis",
                }
            return result
        result = _normalize_result(agent, native_result, input_value, mode, aliases)
        if split:
            result = _merge_structured_phases(
                cast(RunResult, action_normalized),
                action_turns,
                result,
            )
        return attach_native_result(result, native_result)


def _observe_tools(native_agent: Any, aliases: ToolNameAliases) -> list[ToolEvent]:
    """Keep completed calls if the SDK fails before returning its final result.

    Wrappers and evidence belong to this execution, never the cached SDK agent.
    Successful runs still use SDK normalization, so projections are not doubled.
    """
    observed: list[ToolEvent] = []

    def wrap(tool: Any) -> Any:
        invoke = getattr(tool, "on_invoke_tool", None)
        if not callable(invoke):
            return tool
        isolated = copy.copy(tool)

        async def record(context: Any, arguments: str) -> Any:
            identity = str(getattr(context, "tool_call_id", None) or uuid4().hex)
            inputs = copy.deepcopy(_json_object(arguments))
            output = await cast(Any, invoke)(context, arguments)
            data, ok, error = decode_tool_output(_jsonable(output))
            observed.append(
                ToolEvent(
                    id=identity,
                    name=aliases.canonical(tool.name),
                    input=inputs,
                    output=copy.deepcopy({"data": _jsonable(data)}),
                    ok=ok,
                    error=copy.deepcopy(error),
                    meta={"source": "openai-agents"},
                )
            )
            return output

        isolated.on_invoke_tool = record
        return isolated

    native_agent.tools = [wrap(tool) for tool in getattr(native_agent, "tools", ())]
    return observed


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
        from openai import DefaultAsyncHttpxClient
        from .openai_models import ChatCompletionTermination, ToolCallNormalizingModel

        termination = ChatCompletionTermination()
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=DefaultAsyncHttpxClient(
                event_hooks={"response": [termination.observe]}
            ),
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
            termination=termination,
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
    # Enforce at the executable boundary too: model settings are advisory and
    # a provider may emit multiple calls in a single response.
    invoked = 0

    def bounded(invoke: Any) -> Any:
        async def run(context: Any, arguments: str) -> Any:
            nonlocal invoked
            if invoked >= limit:
                return _sdk_tool_failure(
                    context, RuntimeError("max_tool_calls_exhausted")
                )
            invoked += 1
            return await invoke(context, arguments)

        return run

    native_agent.tools = [
        dataclasses.replace(tool, on_invoke_tool=bounded(tool.on_invoke_tool))
        if dataclasses.is_dataclass(tool) and hasattr(tool, "on_invoke_tool")
        else tool
        for tool in native_agent.tools
    ]
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


def _uses_structured_tool_phases(native_agent: Any, policy: RunPolicy) -> bool:
    """Separate executable work from typed synthesis when both are requested.

    A tool call and a final structured value are different protocol boundaries.
    Keeping them in separate SDK runs avoids asking an OpenAI-compatible endpoint
    to satisfy both boundaries in one response, while retaining one public Agent
    invocation and one portable turn/tool budget.
    """

    output_type = getattr(native_agent, "output_type", None)
    executables = bool(
        getattr(native_agent, "tools", ()) or getattr(native_agent, "mcp_servers", ())
    )
    return output_type is not None and executables and policy.max_tool_calls != 0


def _phase_agent(native_agent: Any, **updates: Any) -> Any:
    """Clone a prepared SDK Agent and change only fields present in its version."""

    if dataclasses.is_dataclass(native_agent):
        fields = {field.name for field in dataclasses.fields(native_agent)}
        selected = {key: value for key, value in updates.items() if key in fields}
        return cast(Any, dataclasses.replace(cast(Any, native_agent), **selected))
    phase = copy.copy(native_agent)
    for key, value in updates.items():
        if hasattr(phase, key):
            setattr(phase, key, value)
    return phase


def _native_turn_count(native_result: Any, *, conservative_default: int) -> int:
    """Read SDK request count, falling back to captured responses or the bound."""

    usage = getattr(getattr(native_result, "context_wrapper", None), "usage", None)
    requests = getattr(usage, "requests", None)
    if isinstance(requests, int) and requests > 0:
        return requests
    raw_responses = getattr(native_result, "raw_responses", None)
    if isinstance(raw_responses, (list, tuple)) and raw_responses:
        return len(raw_responses)
    return conservative_default


def _synthesis_agent(native_agent: Any, policy: RunPolicy) -> Any:
    """Create the non-executable typed-output phase without mutating the cache."""

    phase = _phase_agent(
        native_agent,
        tools=[],
        mcp_servers=[],
        handoffs=[],
        input_guardrails=[],
    )
    synthesis_policy = policy.model_copy(
        update={"max_tool_calls": 0, "tool_choice": "none"}
    )
    _configure_native_agent(phase, synthesis_policy)
    return phase


def _remaining_turns(
    action_result: Any,
    *,
    max_turns: int,
    action_bound: int,
) -> int:
    consumed = _native_turn_count(
        action_result,
        conservative_default=action_bound,
    )
    return max(1, max_turns - min(consumed, action_bound))


def _run_structured_synthesis_sync(
    runner: Any,
    native_agent: Any,
    action_result: Any,
    policy: RunPolicy,
    *,
    max_turns: int,
    kwargs: Mapping[str, Any],
) -> Any:
    action_bound = max_turns - 1
    phase = _synthesis_agent(native_agent, policy)
    return runner.run_sync(
        phase,
        action_result.to_input_list(),
        max_turns=_remaining_turns(
            action_result,
            max_turns=max_turns,
            action_bound=action_bound,
        ),
        **dict(kwargs),
    )


async def _run_structured_synthesis_async(
    runner: Any,
    native_agent: Any,
    action_result: Any,
    policy: RunPolicy,
    *,
    max_turns: int,
    kwargs: Mapping[str, Any],
) -> Any:
    action_bound = max_turns - 1
    phase = _synthesis_agent(native_agent, policy)
    return await runner.run(
        phase,
        action_result.to_input_list(),
        max_turns=_remaining_turns(
            action_result,
            max_turns=max_turns,
            action_bound=action_bound,
        ),
        **dict(kwargs),
    )


def _phase_budget_failure(
    agent: Any,
    input_value: Any,
    mode: str,
    max_turns: int,
) -> RunResult:
    message = (
        "Structured output with executable tools requires max_turns >= 2 "
        f"(received {max_turns})."
    )
    result = _failure(agent, input_value, mode, RuntimeError(message))
    result.data = {
        "ok": False,
        "error": {
            "code": "structured_tool_turn_budget",
            "message": message,
        },
    }
    result.errors = [cast(dict[str, Any], result.data["error"])]
    result.meta["structured_execution"] = {
        "strategy": "tools_then_output",
        "failed_phase": "budget_validation",
    }
    return result


def _merge_structured_phases(
    action_result: RunResult,
    action_turns: int,
    synthesis_result: RunResult,
) -> RunResult:
    """Preserve action evidence while exposing the typed synthesis as the answer."""

    synthesis_ok = synthesis_result.ok
    synthesis_usage = copy.deepcopy(synthesis_result.usage)
    synthesis_result.tool_events = [
        *copy.deepcopy(action_result.tool_events),
        *copy.deepcopy(synthesis_result.tool_events),
    ]
    synthesis_result.raw_responses = [
        *copy.deepcopy(action_result.raw_responses),
        *copy.deepcopy(synthesis_result.raw_responses),
    ]
    synthesis_result.usage = merge_usage(action_result.usage, synthesis_result.usage)
    for error in action_result.errors:
        if error not in synthesis_result.errors:
            synthesis_result.errors.append(copy.deepcopy(error))
    if not action_result.ok:
        synthesis_result.ok = False
    synthesis_result.meta["structured_execution"] = {
        "strategy": "tools_then_output",
        "phases": (
            {
                "name": "action",
                "turns": action_turns,
                "tool_events": len(action_result.tool_events),
                "ok": action_result.ok,
            },
            {
                "name": "synthesis",
                "turns": int(synthesis_usage.get("requests") or 0),
                "tool_events": len(synthesis_result.tool_events)
                - len(action_result.tool_events),
                "ok": synthesis_ok,
            },
        ),
    }
    return synthesis_result


def _preserve_failed_action(
    action: RunResult | None,
    failure: RunResult,
    observed: list[ToolEvent],
) -> RunResult:
    """Retain completed phase-one evidence if typed synthesis fails later."""

    if action is None:
        failure.tool_events = copy.deepcopy(observed)
        return failure
    failure.tool_events = copy.deepcopy(action.tool_events or observed)
    failure.messages = copy.deepcopy(action.messages)
    failure.raw_responses = copy.deepcopy(action.raw_responses)
    failure.usage = copy.deepcopy(action.usage)
    for error in action.errors:
        if error not in failure.errors:
            failure.errors.append(copy.deepcopy(error))
    return failure


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
            **({"termination": exc.termination} if hasattr(exc, "termination") else {}),
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
