"""Strands Agents SDK adapter with Provider materialization."""

from __future__ import annotations

import inspect
import json
import os
from collections.abc import Mapping
from functools import update_wrapper
from typing import Any, cast, get_args, get_type_hints

from pydantic import ConfigDict as _ConfigDict
from pydantic import create_model as _create_model

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
from ...tools.parsing import parse_textual_tool_call
from ...tools.events import ToolEvent
from ...usage import normalize_usage
from .base import (
    FrameworkAdapter,
    attach_native_result,
    effective_max_turns,
    validate_policy_support,
)
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
        validate_policy_support(self.name, policy, mode)
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
        message_cursor = _message_cursor(native_agent)
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
            agent,
            native_agent,
            native_result,
            input_value,
            mode,
            aliases,
            message_cursor=message_cursor,
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
            and not agent.framework_config.agent_kwargs.get("tools")
            and provider_capability(agent.engine, "model_generation").status
            == "unsupported"
        ):
            result = await cast(Any, engine).arun(agent, input_value, policy, mode=mode)
            result.meta["framework_adapter"] = self.name
            return result
        native_agent = self.prepare(agent, engine)
        message_cursor = _message_cursor(native_agent)
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
            agent,
            native_agent,
            native_result,
            input_value,
            mode,
            aliases,
            message_cursor=message_cursor,
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
        model_kwargs = {
            "model_id": agent.model,
            "region_name": region_name,
            "boto_session": session,
            "streaming": bool(getattr(runtime, "streaming", False)),
            "boto_client_config": (
                Config(signature_version="v4")
                if auth_mode == "aws-credential-chain"
                else None
            ),
        }
        # Test doubles and vendor shims may expose a factory rather than a
        # subclassable SDK model. They still receive the same public contract.
        if not isinstance(BedrockModel, type):
            return BedrockModel(**model_kwargs)

        class ContractAwareBedrockModel(BedrockModel):
            """Release a forced Tool after the declared contract is satisfied."""

            async def stream(
                self,
                messages: Any,
                tool_specs: list[Any] | None = None,
                system_prompt: str | None = None,
                *,
                tool_choice: Any = None,
                **kwargs: Any,
            ) -> Any:
                contract_satisfied = _contract_tools_satisfied(agent, messages)
                events = [
                    event
                    async for event in super().stream(
                        messages,
                        tool_specs,
                        system_prompt,
                        tool_choice=_budgeted_continuation_tool_choice(
                            self, agent, messages, tool_choice
                        ),
                        **kwargs,
                    )
                ]
                authorized_events = _limit_tool_use_events(
                    self, events, suppress_tools=contract_satisfied
                )
                # Record before yielding: Strands may stop consuming immediately
                # after ToolUse, but the next turn must still see exhausted budget.
                _record_emitted_tool_calls(
                    self,
                    sum(_stream_tool_use_count(event) for event in authorized_events),
                )
                for event in authorized_events:
                    yield event

        return ContractAwareBedrockModel(**model_kwargs)
    if agent.engine in {
        OPENAI_RUNTIME_ENGINE,
        OLLAMA_RUNTIME_ENGINE,
        VLLM_RUNTIME_ENGINE,
    }:
        from strands.models.openai import OpenAIModel

        # Test doubles and vendor shims may expose a factory instead of a class.
        # Native Strands installations expose a class and receive the strict
        # boundary normalizer below.
        if not isinstance(OpenAIModel, type):
            client_args: dict[str, Any] = {}
            endpoint = getattr(agent.runtime_config, "endpoint", None)
            api_key = _runtime_api_key(agent) or os.getenv("OPENAI_API_KEY")
            if endpoint:
                client_args["base_url"] = endpoint
            if api_key:
                client_args["api_key"] = api_key
            return OpenAIModel(model_id=agent.model, client_args=client_args or None)

        class ToolCallNormalizingOpenAIModel(OpenAIModel):
            """Promote strict textual calls emitted by OpenAI-compatible models."""

            def format_request(
                self,
                messages: Any = None,
                tool_specs: list[Any] | None = None,
                system_prompt: str | None = None,
                tool_choice: Any = None,
                *,
                system_prompt_content: list[Any] | None = None,
                **kwargs: Any,
            ) -> dict[str, Any]:
                resolved_choice = _budgeted_continuation_tool_choice(
                    self, agent, messages, tool_choice
                )
                request = super().format_request(
                    messages,
                    tool_specs,
                    system_prompt,
                    resolved_choice,
                    system_prompt_content=system_prompt_content,
                    **kwargs,
                )
                # OpenAIModel merges config.params after the per-turn choice.
                # Make the contract-aware continuation authoritative.
                if resolved_choice == {"auto": {}}:
                    request["tool_choice"] = "auto"
                return request

            async def stream(
                self,
                messages: Any,
                tool_specs: list[Any] | None = None,
                system_prompt: str | None = None,
                *,
                tool_choice: Any = None,
                **kwargs: Any,
            ) -> Any:
                contract_satisfied = _contract_tools_satisfied(agent, messages)
                tool_choice = _budgeted_continuation_tool_choice(
                    self, agent, messages, tool_choice
                )
                events = [
                    event
                    async for event in super().stream(
                        messages,
                        tool_specs,
                        system_prompt,
                        tool_choice=tool_choice,
                        **kwargs,
                    )
                ]
                normalized_events = _normalize_textual_tool_events(events, tool_specs)
                normalized_events = _limit_tool_use_events(
                    self,
                    normalized_events,
                    suppress_tools=contract_satisfied,
                )
                _record_emitted_tool_calls(
                    self,
                    sum(_stream_tool_use_count(event) for event in normalized_events),
                )
                for event in normalized_events:
                    yield event

        model_class = ToolCallNormalizingOpenAIModel
        if agent.engine == VLLM_RUNTIME_ENGINE:

            class VLLMOpenAIModel(ToolCallNormalizingOpenAIModel):
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


def _continuation_tool_choice(
    agent: Any,
    messages: Any,
    tool_choice: Any,
) -> Any:
    """Stop forcing a Tool once successful evidence satisfies the contract.

    Strands applies a model-level Tool choice on every turn. A named/required
    choice is useful for the first turn, but retaining it after a successful
    Tool result creates duplicate calls and prevents the model from producing
    its public final answer. The decision is contract-driven and therefore
    identical for Bedrock and OpenAI-compatible model boundaries.
    """

    if _contract_tools_satisfied(agent, messages):
        return {"auto": {}}
    return tool_choice


def _contract_tools_satisfied(agent: Any, messages: Any) -> bool:
    """Detect successful required Tool evidence across Strands projections."""

    contract = getattr(agent, "contract", None)
    completion = getattr(contract, "completion", None)
    required = set(getattr(contract, "must_call", ()) or ())
    if not required or completion not in {
        "when_contract_satisfied",
        "when_required_tools_satisfied",
    }:
        return False

    aliases = tool_name_aliases(agent.available_tools())
    public_messages = [_jsonable(message) for message in messages or ()]
    successful = {
        event.name for event in _tool_events(public_messages, aliases) if event.ok
    }
    if required.issubset(successful):
        return True
    available = {str(getattr(tool, "name", "")) for tool in agent.available_tools()}
    # Some Strands model boundaries pass only the latest ToolResult to the
    # continuation turn. With one declared Tool its identity is unambiguous.
    return (
        len(required) == 1
        and available == required
        and _has_successful_tool_result(public_messages)
    )


def _budgeted_continuation_tool_choice(
    model: Any,
    agent: Any,
    messages: Any,
    tool_choice: Any,
) -> Any:
    """Resolve per-turn choice and enforce the effective Tool-call budget.

    Message projections differ across Framework SDK versions. The adapter also
    tracks ToolUse blocks it actually emitted, so a forced choice cannot create
    a second call after the declared positive budget has been exhausted.
    """

    resolved = _continuation_tool_choice(agent, messages, tool_choice)
    limit = getattr(model, "_agentic_systems_max_tool_calls", None)
    emitted = getattr(model, "_agentic_systems_emitted_tool_calls", 0)
    if isinstance(limit, int) and limit > 0 and emitted >= limit:
        return {"auto": {}}
    return resolved


def _stream_tool_use_count(event: Any) -> int:
    """Count native ToolUse starts without depending on a provider SDK class."""

    public = _jsonable(event)
    if not isinstance(public, Mapping):
        return 0
    block_start = public.get("contentBlockStart")
    if not isinstance(block_start, Mapping):
        return 0
    start = block_start.get("start")
    return int(isinstance(start, Mapping) and isinstance(start.get("toolUse"), Mapping))


def _record_emitted_tool_calls(model: Any, count: int) -> None:
    if count <= 0:
        return
    current = getattr(model, "_agentic_systems_emitted_tool_calls", 0)
    try:
        setattr(model, "_agentic_systems_emitted_tool_calls", current + count)
    except (AttributeError, TypeError):
        # Immutable third-party shims still use message-based continuation.
        return


def _reset_tool_budget(model: Any, max_tool_calls: int | None) -> None:
    try:
        setattr(model, "_agentic_systems_max_tool_calls", max_tool_calls)
        setattr(model, "_agentic_systems_emitted_tool_calls", 0)
        setattr(model, "_agentic_systems_rejected_tool_calls", [])
    except (AttributeError, TypeError):
        # Not every test double or vendor proxy permits private attributes.
        return


def _limit_tool_use_events(
    model: Any,
    events: list[Any],
    *,
    suppress_tools: bool = False,
) -> list[Any]:
    """Keep only ToolUse blocks authorized by budget and contract completion."""

    limit = getattr(model, "_agentic_systems_max_tool_calls", None)
    if not isinstance(limit, int):
        return events
    emitted = int(getattr(model, "_agentic_systems_emitted_tool_calls", 0) or 0)
    remaining = 0 if suppress_tools else max(0, limit - emitted)
    accepted = 0
    suppress_block = False
    rejected_in_batch = False
    filtered: list[Any] = []
    rejected: list[dict[str, Any]] = list(
        getattr(model, "_agentic_systems_rejected_tool_calls", ()) or ()
    )
    for event in events:
        public = _jsonable(event)
        starts_tool = _stream_tool_use_count(public) > 0
        starts_block = isinstance(public, Mapping) and isinstance(
            public.get("contentBlockStart"), Mapping
        )
        if starts_tool:
            if accepted >= remaining:
                rejected.append(
                    {
                        "name": _stream_tool_use_name(public),
                        "reason": (
                            "contract_satisfied"
                            if suppress_tools
                            else "max_tool_calls_exhausted"
                        ),
                    }
                )
                rejected_in_batch = True
                suppress_block = True
                continue
            accepted += 1
            suppress_block = False
            filtered.append(event)
            continue
        if starts_block:
            suppress_block = False
        if suppress_block:
            if isinstance(public, Mapping) and "contentBlockStop" in public:
                suppress_block = False
            continue
        if (
            rejected_in_batch
            and accepted == 0
            and isinstance(public, Mapping)
            and isinstance(public.get("messageStop"), Mapping)
        ):
            message_stop = dict(public["messageStop"])
            if message_stop.get("stopReason") == "tool_use":
                message_stop["stopReason"] = "end_turn"
            filtered.append({"messageStop": message_stop})
            continue
        filtered.append(event)
    try:
        setattr(model, "_agentic_systems_rejected_tool_calls", rejected)
    except (AttributeError, TypeError):
        pass
    return filtered


def _stream_tool_use_name(event: Any) -> str:
    public = _jsonable(event)
    if not isinstance(public, Mapping):
        return ""
    block_start = public.get("contentBlockStart")
    if not isinstance(block_start, Mapping):
        return ""
    start = block_start.get("start")
    if not isinstance(start, Mapping):
        return ""
    tool_use = start.get("toolUse")
    return str(tool_use.get("name") or "") if isinstance(tool_use, Mapping) else ""


def _has_successful_tool_result(value: Any) -> bool:
    """Recognize a successful native Strands ToolResult at any message depth."""

    if isinstance(value, Mapping):
        result = value.get("toolResult") or value.get("tool_result")
        if isinstance(result, Mapping):
            return str(result.get("status") or "success").lower() == "success"
        return any(_has_successful_tool_result(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_successful_tool_result(item) for item in value)
    return False


def _normalize_textual_tool_events(
    events: list[Any], tool_specs: list[Any] | None
) -> list[Any]:
    """Promote one exact declared name-with-JSON response to ToolUse.

    The normalization is deliberately strict and confined to the external
    Strands/OpenAI-compatible boundary. Prose, code, unknown tools, malformed JSON,
    and responses that already contain native ToolUse blocks are unchanged.
    """

    if any(
        isinstance(event, Mapping)
        and isinstance(event.get("contentBlockStart"), Mapping)
        and isinstance(event["contentBlockStart"].get("start"), Mapping)
        and "toolUse" in event["contentBlockStart"]["start"]
        for event in events
    ):
        return events
    names: list[str] = []
    for spec in tool_specs or []:
        if not isinstance(spec, Mapping):
            continue
        name = spec.get("name")
        if not name and isinstance(spec.get("toolSpec"), Mapping):
            name = spec["toolSpec"].get("name")
        if isinstance(name, str) and name:
            names.append(name)
    text = "".join(
        str(delta["text"])
        for event in events
        if isinstance(event, Mapping)
        and isinstance(event.get("contentBlockDelta"), Mapping)
        and isinstance(event["contentBlockDelta"].get("delta"), Mapping)
        and isinstance((delta := event["contentBlockDelta"]["delta"]).get("text"), str)
    )
    parsed = parse_textual_tool_call(text, names)
    if parsed is None:
        return events
    name, arguments = parsed
    tool_use_id = f"agentic-systems-{name}"
    metadata = [
        event for event in events if isinstance(event, Mapping) and "metadata" in event
    ]
    return [
        {"messageStart": {"role": "assistant"}},
        {
            "contentBlockStart": {
                "start": {"toolUse": {"name": name, "toolUseId": tool_use_id}}
            }
        },
        {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "tool_use"}},
        *metadata,
    ]


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

    schema = _tool_input_json_schema(tool, function)
    native_function = _schema_backed_function(tool, function)
    return cast(Any, strands_tool)(
        native_function,
        name=native_name or tool.name,
        description=tool.description or None,
        inputSchema=schema,
    )


def _schema_backed_function(tool: Any, function: Any) -> Any:
    """Project one explicit public Tool schema onto Strands' callable contract.

    Strands validates invocations from the Python callable signature even when an
    explicit ``inputSchema`` is supplied.  Public Agentic Systems Tools instead
    treat their Pydantic ``input_schema`` as the source of truth.  Build a generic
    keyword callable whose inspectable signature mirrors that schema, then execute
    through ``Tool.run`` so every framework observes the same validation and output
    normalization semantics.
    """

    input_schema = getattr(tool, "input_schema", None)
    run = getattr(tool, "run", None)
    if input_schema is None or not callable(run):
        return function

    def invoke(**payload: Any) -> Any:
        result = run(payload)
        if not result.ok:
            message = result.text or f"Tool '{tool.name}' failed."
            raise ValueError(message)
        return result.data

    update_wrapper(invoke, function)
    parameters: list[inspect.Parameter] = []
    annotations: dict[str, Any] = {}
    for name, field in input_schema.model_fields.items():
        annotation = field.annotation or Any
        default = (
            inspect.Signature.empty
            if field.is_required()
            else field.get_default(call_default_factory=True)
        )
        parameters.append(
            inspect.Parameter(
                name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
        )
        annotations[name] = annotation
    annotations["return"] = get_type_hints(function).get("return", Any)
    invoke.__annotations__ = annotations
    invoke.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters,
        return_annotation=annotations["return"],
    )
    return invoke


def _tool_input_json_schema(tool: Any, function: Any) -> dict[str, Any]:
    """Build the same typed, closed Tool schema for every Strands provider."""

    if tool.input_schema is not None:
        return cast(dict[str, Any], tool.input_schema.model_json_schema())

    signature = inspect.signature(function)
    type_hints = get_type_hints(function)
    fields: dict[str, tuple[Any, Any]] = {}
    for name, parameter in signature.parameters.items():
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            raise TypeError(
                f"Tool '{tool.name}' cannot use *args or **kwargs. "
                "Use explicit typed parameters so a JSON schema can be generated."
            )
        annotation = type_hints.get(name, Any)
        default = (
            ... if parameter.default is inspect.Signature.empty else parameter.default
        )
        fields[name] = (annotation, default)

    model_name = (
        "".join(part.capitalize() for part in tool.name.split("_")) + "ToolInput"
    )
    create_model = cast(Any, _create_model)
    input_model = create_model(
        model_name,
        __config__=_ConfigDict(extra="forbid", arbitrary_types_allowed=True),
        **fields,
    )
    return cast(dict[str, Any], input_model.model_json_schema())


def _configure_model(model: Any, policy: RunPolicy, mode: str) -> None:
    # This state belongs to one public Agent.run invocation. It is deliberately
    # private and is reset even when the Framework caches its native model.
    _reset_tool_budget(model, policy.max_tool_calls)
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
    # Discover the accepted keys from update_config's Unpack[TypedDict] contract
    # instead of inferring the shape from the current (possibly sparse) values.
    declared_keys = _declared_model_config_keys(model)
    nested_params = "params" in declared_keys or (
        not declared_keys and "params" in config
    )
    if not nested_params:
        if declared_keys:
            generation_config = {
                key: value
                for key, value in generation_config.items()
                if key in declared_keys
            }
        if generation_config:
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


def _declared_model_config_keys(model: Any) -> set[str]:
    """Return keys accepted by a Strands update_config Unpack contract."""

    update_config = getattr(type(model), "update_config", None)
    if not callable(update_config):
        return set()
    try:
        annotation = get_type_hints(update_config).get("model_config")
    except (NameError, TypeError):
        return set()
    arguments = get_args(annotation)
    if len(arguments) != 1:
        return set()
    fields = getattr(arguments[0], "__annotations__", None)
    return set(fields) if isinstance(fields, Mapping) else set()


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
    *,
    message_cursor: int = 0,
) -> RunResult:
    provider_result = getattr(native_agent.model, "last_result", None)
    rejected_tool_calls = list(
        getattr(native_agent.model, "_agentic_systems_rejected_tool_calls", ()) or ()
    )
    if isinstance(provider_result, RunResult):
        provider_result.meta["framework_adapter"] = "strands"
        provider_result.meta["input"] = _jsonable(input_value)
        provider_result.meta["rejected_tool_calls"] = rejected_tool_calls
        return provider_result

    structured = getattr(native_result, "structured_output", None)
    raw_value = structured if structured is not None else str(native_result)
    raw_text = _input_text(raw_value)
    text = public_answer_text(raw_value) or raw_text
    data = _output_data(raw_value, raw_text)
    messages = _invocation_messages(native_agent, message_cursor)
    return RunResult(
        text=text,
        final={"text": text},
        data=data,
        ok=True,
        messages=messages,
        tool_events=_tool_events(messages, aliases),
        raw_responses=[_jsonable(getattr(native_result, "message", {}))],
        usage=_strands_usage(getattr(native_result, "metrics", {})),
        engine=agent.engine,
        model=agent.model or "",
        mode=mode,
        meta={
            "source_result_type": type(native_result).__name__,
            "framework_adapter": "strands",
            "input": _jsonable(input_value),
            "stop_reason": getattr(native_result, "stop_reason", None),
            "rejected_tool_calls": rejected_tool_calls,
        },
    )


def _message_cursor(native_agent: Any) -> int:
    """Capture the native transcript boundary before one public invocation."""

    messages = getattr(native_agent, "messages", ())
    try:
        return len(messages)
    except TypeError:
        return 0


def _invocation_messages(native_agent: Any, cursor: int) -> list[Any]:
    """Project only messages created by the current invocation.

    Strands may retain a native conversation across calls. That history remains owned
    by the SDK, while each public RunResult and its policy validation describe exactly
    one invocation.
    """

    messages = getattr(native_agent, "messages", ())
    try:
        current = messages[cursor:]
    except (IndexError, TypeError):
        current = messages
    return [_jsonable(item) for item in current]


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
                        output=_strands_tool_output(result.get("content")),
                        ok=status == "success",
                        error=None if status == "success" else {"status": status},
                        meta={"source": "strands"},
                    )
                )
    return events


def _strands_tool_output(value: Any) -> dict[str, Any]:
    """Decode Strands content blocks into stable public Tool evidence."""

    payload = _jsonable(value)
    if isinstance(payload, list):
        decoded: list[Any] = []
        for block in payload:
            if isinstance(block, Mapping) and "json" in block:
                decoded.append(block["json"])
            elif isinstance(block, Mapping) and isinstance(block.get("text"), str):
                decoded.append(_decode_json_text(block["text"]))
            else:
                decoded.append(block)
        payload = decoded[0] if len(decoded) == 1 else {"items": decoded}
    if isinstance(payload, str):
        payload = _decode_json_text(payload)
    if isinstance(payload, Mapping):
        public = dict(payload)
        answer = public.get("answer") or public.get("text")
        if isinstance(answer, str) and answer:
            return {"text": answer, "evidence": public}
        return public
    return {"value": payload}


def _decode_json_text(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


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


def _strands_usage(metrics: Any) -> dict[str, Any]:
    """Project public EventLoopMetrics without depending on SDK internals."""

    summary_method = getattr(metrics, "get_summary", None)
    if callable(summary_method):
        summary = _json_dict(summary_method())
    else:
        summary = _json_dict(metrics)
    accumulated_usage = _json_dict(summary.get("accumulated_usage", summary))
    payload = normalize_usage(accumulated_usage)

    accumulated_metrics = _json_dict(summary.get("accumulated_metrics", {}))
    service_latency = accumulated_metrics.get("latencyMs")
    if (
        isinstance(service_latency, (int, float))
        and not isinstance(service_latency, bool)
        and service_latency > 0
    ):
        payload["service_latency_ms"] = service_latency

    total_duration = summary.get("total_duration")
    if isinstance(total_duration, (int, float)) and not isinstance(
        total_duration, bool
    ):
        payload["client_duration_ms"] = round(total_duration * 1000, 3)

    cycles = summary.get("total_cycles")
    if isinstance(cycles, int) and not isinstance(cycles, bool) and cycles > 0:
        payload["requests"] = cycles
    return normalize_usage(payload)


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
