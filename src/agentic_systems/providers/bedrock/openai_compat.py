from __future__ import annotations

import asyncio
import concurrent.futures
import json
import uuid
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Sequence


from .models import RuntimeToolSpec


class _OpenAICompatMixin:
    def as_openai_runtime_tools(
        self, tool_names: Optional[Sequence[str]] = None
    ) -> List[Any]:
        """
        Convert neutral ADA tools into OpenAI runtime FunctionTool objects.

        Important contract:
        - The SDK may orchestrate tool calls.
        - BedrockRuntime must execute every tool call.
        - Every tool output must be a ToolEnvelope JSON string.

        We intentionally avoid the SDK `function_tool(...)` decorator here because
        it can intercept validation errors and return framework-owned text such as
        "An error occurred while running the tool" before the runtime can
        canonize the failure. Manual FunctionTool wiring keeps the bridge strict
        and runtime-agnostic.
        """

        return [
            self._make_openai_function_tool(spec)
            for spec in self._select_tools(tool_names)
        ]

    @staticmethod
    def _coerce_framework_tool_arguments(raw_args: Any) -> Any:
        """Coerce framework-provided tool arguments into a JSON-like object.

        The OpenAI runtime documents ``on_invoke_tool`` arguments as a JSON
        string, but runtimes should not depend on that representation. Across
        SDK versions, tests, or custom runners, the value may already be a dict,
        may be bytes, or may be an object exposing pydantic/model-dump methods.
        This helper is intentionally generic and does not know any tool names.
        """

        if raw_args is None or raw_args == "":
            return {}

        if isinstance(raw_args, dict):
            return raw_args

        if isinstance(raw_args, bytes):
            raw_args = raw_args.decode("utf-8")

        if isinstance(raw_args, str):
            return json.loads(raw_args)

        if hasattr(raw_args, "model_dump"):
            return raw_args.model_dump(mode="json")

        if hasattr(raw_args, "dict"):
            return raw_args.dict()

        return raw_args

    @staticmethod
    def _ensure_openai_strict_json_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Return an OpenAI-compatible strict JSON schema without tool-specific logic.

        The runtime recommends strict JSON schema for FunctionTool. Some SDK
        versions do not fully normalize schemas supplied to FunctionTool directly,
        so the runtime makes the neutral tool schema explicit: object schemas get
        ``properties`` and ``additionalProperties=False`` recursively.
        """

        def _strict(node: Any) -> Any:
            if isinstance(node, list):
                return [_strict(item) for item in node]
            if not isinstance(node, dict):
                return node

            out = {key: _strict(value) for key, value in node.items()}

            node_type = out.get("type")
            if node_type == "object" or "properties" in out:
                out.setdefault("type", "object")
                out.setdefault("properties", {})
                out["additionalProperties"] = False
                if isinstance(out.get("properties"), dict):
                    out["properties"] = {
                        key: _strict(value) for key, value in out["properties"].items()
                    }

            if "items" in out:
                out["items"] = _strict(out["items"])

            for combinator in ("anyOf", "oneOf", "allOf"):
                if combinator in out:
                    out[combinator] = _strict(out[combinator])

            return out

        return _strict(dict(schema or {"type": "object", "properties": {}}))

    @classmethod
    def _openai_function_tool_schema(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a neutral tool schema for OpenAI runtime FunctionTool."""

        strict_schema = cls._ensure_openai_strict_json_schema(schema)
        try:
            from agents.strict_schema import ensure_strict_json_schema

            return ensure_strict_json_schema(strict_schema)
        except Exception:
            return strict_schema

    def _make_openai_function_tool(self, spec: RuntimeToolSpec) -> Any:
        """Create a native OpenAI runtime FunctionTool backed by execute_tool().

        This is intentionally native SDK usage: Agent + Runner + FunctionTool +
        ModelProvider. The runtime only owns the tool contract and Bedrock model
        transport; it does not replace the SDK loop with run_direct().
        """

        from agents import FunctionTool

        async def _on_invoke_tool(context: Any, raw_args: Any) -> str:
            try:
                parsed_args = self._coerce_framework_tool_arguments(raw_args)

                if not isinstance(parsed_args, dict):
                    envelope = self.to_envelope(
                        {
                            "error_type": "InvalidToolArguments",
                            "message": "Tool arguments must be a JSON object after bridge coercion.",
                            "raw_arguments": self._make_jsonable(raw_args),
                            "coerced_arguments": self._make_jsonable(parsed_args),
                        },
                        tool_name=spec.name,
                        ok=False,
                        extra_meta={
                            "bridge": "openai_runtime",
                            "handled_by": "_make_openai_function_tool",
                        },
                    )
                    return envelope.model_dump_json()

                envelope = self.execute_tool(spec.name, parsed_args)
                return envelope.model_dump_json()

            except Exception as exc:
                envelope = self.to_envelope(
                    {
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                        "raw_arguments": self._make_jsonable(raw_args),
                    },
                    tool_name=spec.name,
                    ok=False,
                    extra_meta={
                        "bridge": "openai_runtime",
                        "handled_by": "_make_openai_function_tool",
                    },
                )
                return envelope.model_dump_json()

        return FunctionTool(
            name=spec.name,
            description=spec.description,
            params_json_schema=self._openai_function_tool_schema(spec.input_schema),
            on_invoke_tool=_on_invoke_tool,
            strict_json_schema=True,
        )

    def _make_openai_tool_wrapper(self, spec: RuntimeToolSpec) -> Callable[..., str]:
        """
        Internal helper retained for downstream stability. Prefer
        _make_openai_function_tool(), which avoids SDK-side error text leakage.
        """

        @wraps(spec.func)
        def _wrapper(*args: Any, **kwargs: Any) -> str:
            bound = spec.signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            envelope = self.execute_tool(spec.name, dict(bound.arguments))
            return envelope.model_dump_json()

        _wrapper.__name__ = spec.name
        _wrapper.__qualname__ = spec.name
        _wrapper.__doc__ = spec.description
        _wrapper.__signature__ = spec.signature

        return _wrapper

    def create_openai_agent(
        self,
        *,
        name: str,
        instructions: str,
        tool_names: Optional[Sequence[str]] = None,
    ) -> Any:
        """Create an OpenAI runtime Agent backed by this runtime's tools."""

        from agents import Agent, set_tracing_disabled

        if self.disable_openai_runtime_tracing:
            set_tracing_disabled(True)

        return Agent(
            name=name,
            instructions=instructions,
            tools=self.as_openai_runtime_tools(tool_names),
        )

    def openai_runtime_model_provider(self) -> Any:
        """Return an OpenAI runtime ModelProvider that calls Bedrock Converse."""

        from agents import Model, ModelProvider, ModelSettings
        from agents.items import (
            ModelResponse,
            ResponseFunctionToolCall,
            ResponseOutputMessage,
            ResponseOutputText,
            Usage,
        )

        runtime = self

        class BedrockOpenAIAgentsModel(Model):
            def __init__(self, model_name: str) -> None:
                self.model_name = model_name

            async def get_response(
                self,
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                *,
                previous_response_id=None,
                conversation_id=None,
                prompt=None,
            ) -> ModelResponse:
                settings = self._coerce_settings(model_settings)

                messages, extra_system = runtime._openai_input_to_bedrock_messages(
                    input
                )
                unresolved_failed_tools = (
                    runtime._openai_unresolved_failed_tools_from_input(input)
                )

                system_blocks: List[Dict[str, str]] = []
                if system_instructions:
                    system_blocks.append({"text": str(system_instructions)})
                system_blocks.extend(extra_system)
                if unresolved_failed_tools:
                    repair_items = []
                    for failure in unresolved_failed_tools:
                        repair_items.append(
                            {
                                "tool_name": failure.get("tool_name"),
                                "failed_input": failure.get("input"),
                                "error_type": failure.get("error_type"),
                                "error_data": failure.get("output_data"),
                            }
                        )
                    system_blocks.append(
                        {
                            "text": (
                                "Hay toolResult con ok=false que siguen sin recuperarse. "
                                "No redactes una respuesta final todavía. Vuelve a llamar las tools fallidas "
                                "con argumentos completos y válidos, usando la evidencia disponible en el historial. "
                                "No repitas tools que ya tienen ToolEnvelope ok=true salvo que sean necesarias como entrada. "
                                f"Fallas pendientes: {json.dumps(repair_items, ensure_ascii=False)}"
                            )
                        }
                    )

                bedrock_tools = runtime._openai_tools_to_bedrock_tools(tools or [])
                requested_tool_choice = getattr(settings, "tool_choice", None)
                if runtime._openai_input_has_tool_results(input):
                    if unresolved_failed_tools:
                        requested_tool_choice = "any"
                    elif requested_tool_choice in {"required", "any"}:
                        # Same policy as run_direct(): require tools on the first turn,
                        # then allow the model to produce the final answer after it has
                        # received successful tool results.
                        requested_tool_choice = "auto"

                bedrock_tool_choice = runtime._openai_tool_choice_to_bedrock(
                    requested_tool_choice,
                    bool(bedrock_tools),
                )

                response = runtime.converse(
                    model_id=self.model_name,
                    messages=messages,
                    system=system_blocks or None,
                    tools=bedrock_tools or None,
                    tool_choice=bedrock_tool_choice,
                    max_tokens=getattr(settings, "max_tokens", None),
                    temperature=getattr(settings, "temperature", None),
                    top_p=getattr(settings, "top_p", None),
                )

                return self._bedrock_to_model_response(response)

            async def stream_response(
                self,
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                *,
                previous_response_id=None,
                conversation_id=None,
                prompt=None,
            ):
                raise NotImplementedError(
                    "BedrockRuntime light version supports non-streaming Converse only."
                )

            @staticmethod
            def _coerce_settings(model_settings: Any) -> Any:
                if model_settings is None:
                    return ModelSettings()
                if isinstance(model_settings, dict):
                    return ModelSettings(**model_settings)
                return model_settings

            @staticmethod
            def _bedrock_to_model_response(response: Dict[str, Any]) -> ModelResponse:
                output_items: List[Any] = []
                content = (
                    response.get("output", {}).get("message", {}).get("content", [])
                )

                for block in content:
                    if "text" in block and str(block["text"]).strip():
                        output_items.append(
                            ResponseOutputMessage(
                                id=f"msg_{uuid.uuid4().hex}",
                                type="message",
                                role="assistant",
                                status="completed",
                                content=[
                                    ResponseOutputText(
                                        type="output_text",
                                        text=str(block["text"]),
                                        annotations=[],
                                    )
                                ],
                            )
                        )

                    elif "toolUse" in block:
                        tool_use = block.get("toolUse") or {}
                        tool_use_id = str(tool_use.get("toolUseId") or "").strip()
                        tool_name = str(tool_use.get("name") or "").strip()

                        if not tool_use_id or not tool_name:
                            # Do not emit an invalid ResponseFunctionToolCall.
                            # If it later re-enters the Bedrock history, Bedrock
                            # rejects the whole request because toolUse.name has
                            # min length 1.
                            output_items.append(
                                ResponseOutputMessage(
                                    id=f"msg_{uuid.uuid4().hex}",
                                    type="message",
                                    role="assistant",
                                    status="completed",
                                    content=[
                                        ResponseOutputText(
                                            type="output_text",
                                            text=(
                                                "[BedrockRuntime] Ignoré un toolUse inválido "
                                                "emitido por el modelo porque no tenía nombre de tool."
                                            ),
                                            annotations=[],
                                        )
                                    ],
                                )
                            )
                            continue

                        output_items.append(
                            ResponseFunctionToolCall(
                                id=f"fc_{tool_use_id}",
                                type="function_call",
                                call_id=tool_use_id,
                                name=tool_name,
                                arguments=json.dumps(
                                    tool_use.get("input", {}),
                                    ensure_ascii=False,
                                ),
                                status="completed",
                            )
                        )

                usage_raw = response.get("usage", {}) or {}
                request_id = response.get("ResponseMetadata", {}).get("RequestId")

                usage = Usage(
                    requests=1,
                    input_tokens=usage_raw.get("inputTokens", 0),
                    output_tokens=usage_raw.get("outputTokens", 0),
                    total_tokens=usage_raw.get("totalTokens", 0),
                )

                return ModelResponse(
                    output=output_items,
                    usage=usage,
                    response_id=request_id,
                    request_id=request_id,
                )

        class BedrockOpenAIAgentsModelProvider(ModelProvider):
            def get_model(self, model_name: Optional[str]) -> Model:
                return BedrockOpenAIAgentsModel(model_name or runtime.model_id)

        return BedrockOpenAIAgentsModelProvider()

    def _openai_run_config(
        self,
        *,
        model_id: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """Build a RunConfig for OpenAI runtime executions."""

        from agents import ModelSettings, RunConfig

        settings = ModelSettings(
            max_tokens=max_tokens or self.max_tokens_default,
            temperature=self.temperature_default
            if temperature is None
            else temperature,
            tool_choice=tool_choice,
        )
        return RunConfig(
            model_provider=self.openai_runtime_model_provider(),
            model=model_id or self.model_id,
            model_settings=settings,
        )

    def run_openai_agent_sync(
        self,
        *,
        agent: Any,
        prompt: str,
        model_id: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_turns: Optional[int] = 12,
    ) -> Any:
        """Run an OpenAI Agents SDK Agent through the sync ``Runner`` path.

        ``agents.Runner.run_sync`` owns an asyncio event loop internally. That
        is fine in scripts, but notebooks and async apps already have a running
        loop. In that case we isolate the SDK sync runner in a worker thread so
        public ``agent.run(...)`` remains usable without patching the notebook
        event loop or requiring ``nest_asyncio``. Async callers should still
        prefer ``agent.arun(...)`` because it uses the SDK's native async path.
        """

        from agents import Runner

        run_config = self._openai_run_config(
            model_id=model_id,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        def _run() -> Any:
            return Runner.run_sync(
                agent,
                prompt,
                max_turns=max_turns,
                run_config=run_config,
            )

        if _has_running_event_loop():
            return _run_in_worker_thread(_run)
        return _run()


def _has_running_event_loop() -> bool:
    """Return True when called from a thread with an active asyncio loop."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _run_in_worker_thread(fn: Callable[[], Any]) -> Any:
    """Run a blocking function in a short-lived worker thread.

    This keeps sync APIs usable from notebooks without mutating global event
    loop policy. Exceptions raised by ``fn`` are propagated unchanged.
    """

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        return future.result()
