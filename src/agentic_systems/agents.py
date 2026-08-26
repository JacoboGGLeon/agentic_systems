"""Canonical Agent facade for Agentic Systems 2.0."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any

from .contracts import (
    AgentContract,
    RunPolicy,
    ValidationResult,
    resolve_policy,
    validate_contract_policy,
)
from .core.runtime import RuntimeConfig
from .core.scheduler import (
    SchedulerConfig,
    SchedulerTimeoutError,
    execute_async,
    execute_sync,
    merge_policy_with_scheduler,
)
from .engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    LANGGRAPH_ORCHESTRATOR,
    PYTHON_RUNTIME_ENGINE,
    canonical_engine_name,
    normalize_engine_text,
)
from .errors import GraphContractError, is_transient_exception
from .integrations.config import FrameworkConfig
from .results import RunResult
from .execution import CompiledSystem, ExecutionPlan, SequentialPlan
from .final_answer import OutputSchema, final_answer
from .skills import LoadedSkill, Skill
from .tools import Tool
from .tools.toolkit import Toolkit, expand_tool_inputs


def _coerce_input(value: Any, input_contract: Any | None) -> Any:
    if input_contract is None:
        return value
    if isinstance(value, input_contract):
        return value
    if isinstance(value, dict):
        return input_contract.model_validate(value)
    return input_contract.model_validate({"input": value})


def _coerce_output_data(result: RunResult, output_contract: Any | None) -> RunResult:
    if output_contract is None:
        if not result.final:
            result.final = final_answer(result.data, text=result.text)
        return result

    if isinstance(output_contract, OutputSchema):
        result.final = final_answer(
            result.data or result.final, schema=output_contract, text=result.text
        )
        return result

    # Pydantic output contracts validate ``data`` and define the final payload.
    # The validated payload also becomes ``final`` because it represents the
    # user-facing structured answer requested by the output contract.
    source = result.data or result.final or _try_parse_json_object(result.text)
    if (
        isinstance(source, dict)
        and set(source) == {"text"}
        and source.get("text") == result.text
    ):
        source = _try_parse_json_object(result.text)
    validated = output_contract.model_validate(source)
    payload = validated.model_dump(mode="json")
    result.data = payload
    result.final = payload
    return result


def _try_parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except Exception:
        return {"text": text}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _resolve_framework_and_engine(
    engine: str | None, framework: str | None
) -> tuple[str, str | None]:
    """Return (execution_engine, user_framework).

    ``engine`` describes the model/runtime provider, while ``framework``
    describes the orchestration layer.
    """

    requested_engine = normalize_engine_text(engine or BEDROCK_RUNTIME_ENGINE)
    if requested_engine == LANGGRAPH_ORCHESTRATOR:
        raise ValueError(
            "langgraph_is_not_engine: LangGraph is an orchestrator, not an engine. Use framework='langgraph' with engine='bedrock-runtime'."
        )
    return canonical_engine_name(requested_engine), framework


def _framework_label(framework: str | None) -> str:
    return (
        str(framework).strip()
        if framework not in (None, "", "n/a")
        else "agentic-systems"
    )


def _framework_metadata(
    framework: str | None, *, adapter: str | None = None
) -> dict[str, Any]:
    requested = str(framework).strip() if framework not in (None, "", "n/a") else None
    return {
        "framework": requested or "agentic-systems",
        "framework_requested": requested,
        "framework_adapter": adapter,
    }


class Agent:
    """Portable agent configuration and execution facade.

    ``Agent`` can now be created directly as a lightweight public API object:

    .. code-block:: python

        agent = Agent(name="calculator", tools=[sumar], skills=[math_skill])

    A direct agent is a portable configuration. By default it targets the
    canonical cloud engine, ``bedrock-runtime``. Use ``agent.bind(system)`` or
    create the agent through ``system.agent(...)`` to run with AWS credentials.
    For smoke tests without AWS, opt in explicitly with ``engine="python-runtime"``
    and pass a structured tool plan.
    """

    def __init__(
        self,
        *,
        name: str,
        instructions: str = "",
        tools: Any = None,
        skills: Any = None,
        system: Any | None = None,
        engine: str | None = None,
        framework: str | FrameworkConfig | None = None,
        model: str | None = None,
        contract: AgentContract | dict[str, Any] | None = None,
        policy: RunPolicy | dict[str, Any] | None = None,
        input_contract: Any | None = None,
        output_contract: Any | None = None,
        input: Any | None = None,
        output: Any | None = None,
        defaults: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        runtime: RuntimeConfig | dict[str, Any] | None = None,
    ) -> None:
        self.system = system
        self.name = str(name or "").strip()
        if not self.name:
            raise ValueError("Agent name must be non-empty.")
        self.instructions = str(instructions or "")
        self.runtime_config = (
            RuntimeConfig.coerce(runtime)
            if runtime is not None
            else getattr(system, "runtime_config", None)
        )
        if self.runtime_config is not None and engine is None:
            engine = self.runtime_config.provider
        self._engine_was_default = engine is None and framework is None
        self.framework_config = FrameworkConfig.coerce(framework)
        framework_name = None if framework is None else self.framework_config.name
        self.engine, self.framework = _resolve_framework_and_engine(
            engine, framework_name
        )
        self._native_agent: Any = None
        self.model = (
            model
            if model is not None
            else (
                self.runtime_config.model_id
                if self.runtime_config
                else getattr(system, "model", None)
            )
        )
        self.contract = AgentContract.coerce(contract)
        self.policy = policy
        self.input_contract = input_contract if input_contract is not None else input
        self.output_contract = (
            output_contract if output_contract is not None else output
        )
        self.defaults = defaults
        self.metadata = dict(metadata or {})

        explicit_tool_names, explicit_tools = _normalize_agent_tool_inputs(tools)
        skill_tool_names, skill_names, skill_tools, skill_objects = (
            _normalize_agent_skill_inputs(skills)
        )
        self.tools = _dedupe_preserve_order([*skill_tool_names, *explicit_tool_names])
        self.skills = _dedupe_preserve_order(skill_names)
        self._direct_tools = _dedupe_tools([*skill_tools, *explicit_tools])
        self._direct_skills = _dedupe_skills(skill_objects)

        self.validate().raise_if_failed()

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return this agent's resolved tool names."""

        return self.tools

    def pipeline(
        self,
        *steps: Any,
        execution: ExecutionPlan | None = None,
        name: str | None = None,
    ) -> CompiledSystem:
        """Compile this Agent and optional stages as its internal pipeline."""

        units = (self, *steps)
        invalid = [unit for unit in units if not callable(getattr(unit, "run", None))]
        if invalid:
            raise TypeError("Agent.pipeline(...) stages must implement run(...).")
        return CompiledSystem(
            name=name or f"agent:{self.name}:pipeline",
            units=units,
            plan=execution or SequentialPlan(),
        )

    def available_tools(self) -> list[Tool]:
        """Return concrete Tool objects known by this agent.

        Direct agents can hold concrete tools from ``tools=[...]`` and
        ``skills=[Skill(...)]``. System-backed agents may only know tool names,
        so this method falls back to the system public registry when available.
        """

        tools = list(self._direct_tools)
        known = {tool.name for tool in tools}
        public_tools = getattr(getattr(self, "system", None), "public_tools", None)
        if public_tools is not None:
            for name in self.tools:
                tool = public_tools.get(name)
                if isinstance(tool, Tool) and tool.name not in known:
                    tools.append(tool)
                    known.add(tool.name)
        return tools

    def info(self) -> dict[str, Any]:
        """Return a JSON-like summary of the agent configuration."""

        runtime_engine = self._runtime_engine_name()
        return {
            "name": self.name,
            "instructions": self.instructions,
            "tools": list(self.tools),
            "skills": list(self.skills),
            "engine": runtime_engine,
            "framework": _framework_label(self.framework),
            "framework_config": self.framework_config.inspect(),
            "runtime_engine": runtime_engine,
            "execution_engine": self.engine,
            "model": self.model,
            "contract": self.contract.model_dump(mode="json"),
            "policy": _json_like(self.policy),
            "input_contract": _contract_name(self.input_contract),
            "output_contract": _contract_name(self.output_contract),
            "has_system": self.system is not None,
            "direct_tool_count": len(self._direct_tools),
            "direct_tools": [tool.info() for tool in self._direct_tools],
            "metadata": _json_like(self.metadata),
            "runtime": self.runtime_config.to_dict()
            if self.runtime_config is not None
            else None,
        }

    def describe(self) -> str:
        """Return a short human-readable description."""

        tools = ", ".join(self.tools) if self.tools else "no tools"
        skills = f"; skills: {', '.join(self.skills)}" if self.skills else ""
        return f"Agent `{self.name}` ({tools}{skills})"

    def check(self) -> ValidationResult:
        """Alias for ``validate`` for symmetry with Tool and Skill."""

        return self.validate()

    def bind(self, system: Any) -> "Agent":
        """Attach this direct agent to an ``AgenticSystem``.

        The method returns the system-backed agent created by ``system.agent``.
        Concrete direct tools are registered first through runtime ``Skill``
        expansion or explicit tool registration paths.
        """

        if system is None:
            raise TypeError("agent.bind(system) expects an AgenticSystem-like object.")
        if self.system is system:
            return self

        skills_payload: list[Any] = [*self._direct_skills]
        known_from_skills = {
            tool.name
            for skill in self._direct_skills
            for tool in skill.available_tools()
        }
        tools_payload: list[Any] = [
            tool for tool in self._direct_tools if tool.name not in known_from_skills
        ]
        tools_payload.extend(
            name
            for name in self.tools
            if name not in {tool.name for tool in self._direct_tools}
        )

        return system.agent(
            name=self.name,
            instructions=self.instructions,
            tools=tools_payload,
            skills=skills_payload or list(self.skills),
            engine=self.engine,
            framework=None if self.framework is None else self.framework_config,
            input=self.input_contract,
            output=self.output_contract,
            contract=self.contract,
            policy=self.policy,
            model=self.model,
            defaults=self.defaults,
            runtime=self.runtime_config,
        )

    @property
    def native_agent(self) -> Any:
        """Return the Framework SDK agent built by prepare() or first execution."""

        return self._native_agent

    def _provider_engine(self) -> Any:
        if self.system is None:
            if self.engine != PYTHON_RUNTIME_ENGINE:
                raise RuntimeError(
                    f"Direct Agent execution without AgenticSystem cannot use provider={self.engine!r}. "
                    "Bind the agent to a system for runtime-backed execution."
                )
            from .providers.python_runtime import PythonRuntimeEngine

            return PythonRuntimeEngine()
        return self._bind_resolved_engine(self.system._engine(self.engine))

    def _bind_resolved_engine(self, engine: Any) -> Any:
        if self.engine != "auto":
            return engine
        resolved = canonical_engine_name(getattr(engine, "name", self.engine))
        if resolved != "auto":
            self.metadata.setdefault("requested_engine", "auto")
            self.engine = resolved
        return engine

    def prepare(self) -> "Agent":
        """Build the native Framework agent without model or MCP execution."""

        from .integrations.adapters import framework_adapter

        engine = self._provider_engine()
        adapter = framework_adapter(self.framework_config.name)
        adapter.prepare(self, engine)
        return self

    def run(
        self,
        input: Any = None,
        *,
        mode: str = "eval",
        config: RunPolicy | dict[str, Any] | None = None,
    ) -> RunResult:
        """Run the agent from synchronous user code.

        This is the primary execution method for notebooks, scripts and tests.
        The selected engine is responsible for using its native synchronous
        path, so sync execution does not create a second event loop behind the
        user's back. Use ``agent.arun(...)`` for async applications and async
        LangGraph nodes.
        """

        clean_input = _coerce_input(input, self.input_contract)
        policy = self._policy_for_runtime(
            resolve_policy(mode=mode, agent_policy=self.policy, run_config=config)
        )
        scheduler = self._scheduler()
        if self.system is None:
            if self.engine != PYTHON_RUNTIME_ENGINE:
                raise RuntimeError(
                    f"Direct Agent.run(...) without AgenticSystem cannot use engine={self.engine!r}. "
                    "Use `agent.bind(system)` or create the agent through `system.agent(...)` for runtime-backed execution."
                )
            from .providers.python_runtime import PythonRuntimeEngine

            engine = PythonRuntimeEngine()
        else:
            engine = self._bind_resolved_engine(self.system._engine(self.engine))
        from .integrations.adapters import framework_adapter

        adapter = framework_adapter(self.framework_config.name)

        def _run_engine() -> RunResult:
            return adapter.run(self, engine, clean_input, policy, mode=mode)

        if scheduler is None:
            result = _run_engine()
            return self._finalize_result(result, clean_input)

        try:
            result, scheduler_meta = execute_sync(
                _run_engine,
                scheduler,
                is_success=lambda item: bool(getattr(item, "ok", True)),
                should_retry_value=lambda item: item.should_retry(),
                should_retry_exception=is_transient_exception,
            )
        except SchedulerTimeoutError as exc:
            result = self._scheduler_failure_result(
                str(exc), clean_input, mode=mode, code="scheduler_timeout"
            )
            scheduler_meta = {
                "scheduler": scheduler.to_dict(),
                "attempts": int(scheduler.max_retries) + 1,
                "retries": int(scheduler.max_retries),
                "timed_out": True,
            }
        except Exception as exc:  # noqa: BLE001 - return scheduler/runtime failures as RunResult.
            result = self._scheduler_failure_result(
                str(exc), clean_input, mode=mode, code=type(exc).__name__
            )
            actual_attempts = int(getattr(exc, "_agentic_scheduler_attempts", 1))
            scheduler_meta = {
                "scheduler": scheduler.to_dict(),
                "attempts": actual_attempts,
                "retries": max(0, actual_attempts - 1),
                "timed_out": False,
            }
        return self._finalize_result(
            self._attach_scheduler_meta(result, scheduler_meta), clean_input
        )

    async def arun(
        self,
        input: Any = None,
        *,
        mode: str = "eval",
        config: RunPolicy | dict[str, Any] | None = None,
    ) -> RunResult:
        """Run the agent from async application code.

        Async execution uses the engine's native async path when available. If a
        custom sync-only engine is plugged in, Agentic Systems isolates that work
        in a worker thread instead of blocking the caller's event loop.
        """

        clean_input = _coerce_input(input, self.input_contract)
        policy = self._policy_for_runtime(
            resolve_policy(mode=mode, agent_policy=self.policy, run_config=config)
        )
        scheduler = self._scheduler()
        if self.system is None:
            if self.engine != PYTHON_RUNTIME_ENGINE:
                raise RuntimeError(
                    f"Direct Agent.arun(...) without AgenticSystem cannot use engine={self.engine!r}. "
                    "Use `agent.bind(system)` or create the agent through `system.agent(...)` for runtime-backed execution."
                )
            from .providers.python_runtime import PythonRuntimeEngine

            engine = PythonRuntimeEngine()
        else:
            engine = self._bind_resolved_engine(self.system._engine(self.engine))
        from .integrations.adapters import framework_adapter

        adapter = framework_adapter(self.framework_config.name)

        async def _run_engine() -> RunResult:
            return await adapter.arun(self, engine, clean_input, policy, mode=mode)

        if scheduler is None:
            result = await _run_engine()
            return self._finalize_result(result, clean_input)

        try:
            result, scheduler_meta = await execute_async(
                _run_engine,
                scheduler,
                is_success=lambda item: bool(getattr(item, "ok", True)),
                should_retry_value=lambda item: item.should_retry(),
                should_retry_exception=is_transient_exception,
            )
        except SchedulerTimeoutError as exc:
            result = self._scheduler_failure_result(
                str(exc), clean_input, mode=mode, code="scheduler_timeout"
            )
            scheduler_meta = {
                "scheduler": scheduler.to_dict(),
                "attempts": int(scheduler.max_retries) + 1,
                "retries": int(scheduler.max_retries),
                "timed_out": True,
            }
        except Exception as exc:  # noqa: BLE001 - return scheduler/runtime failures as RunResult.
            result = self._scheduler_failure_result(
                str(exc), clean_input, mode=mode, code=type(exc).__name__
            )
            actual_attempts = int(getattr(exc, "_agentic_scheduler_attempts", 1))
            scheduler_meta = {
                "scheduler": scheduler.to_dict(),
                "attempts": actual_attempts,
                "retries": max(0, actual_attempts - 1),
                "timed_out": False,
            }
        return self._finalize_result(
            self._attach_scheduler_meta(result, scheduler_meta), clean_input
        )

    def _scheduler(self) -> SchedulerConfig | None:
        if self.runtime_config is None:
            return None
        return self.runtime_config.scheduler

    def _policy_for_runtime(self, policy: RunPolicy) -> RunPolicy:
        return merge_policy_with_scheduler(policy, self._scheduler())

    def _attach_scheduler_meta(
        self, result: RunResult, scheduler_meta: dict[str, Any]
    ) -> RunResult:
        if self.runtime_config is not None:
            result.meta.setdefault("runtime", self.runtime_config.to_dict())
            result.meta.setdefault("scheduler", self.runtime_config.scheduler.to_dict())
        result.meta["scheduler_execution"] = scheduler_meta
        result.usage.setdefault("scheduler", {})
        latency_ms = scheduler_meta.get("latency_ms")
        result.usage["scheduler"].update(
            {
                "attempts": scheduler_meta.get("attempts"),
                "retries": scheduler_meta.get("retries"),
                "timed_out": scheduler_meta.get("timed_out"),
                "latency_ms": latency_ms,
            }
        )
        if isinstance(latency_ms, (int, float)) and not isinstance(latency_ms, bool):
            result.usage.setdefault("client_duration_ms", latency_ms)
        return result

    def _scheduler_failure_result(
        self, message: str, clean_input: Any, *, mode: str, code: str
    ) -> RunResult:
        runtime_engine = self._runtime_engine_name()
        return RunResult(
            text=message,
            data={"ok": False, "error": {"code": code, "message": message}},
            ok=False,
            engine=runtime_engine,
            model=self.model or "",
            mode=mode,
            meta={
                "input": _json_like(clean_input),
                "source_result_type": "SchedulerFailure",
                **_framework_metadata(
                    self.framework, adapter=self.framework_config.name
                ),
                "runtime_engine": runtime_engine,
                "execution_engine": self.engine,
            },
        )

    def _runtime_engine_name(self) -> str:
        return self.engine

    def _finalize_result(
        self, result: RunResult, clean_input: Any | None = None
    ) -> RunResult:
        adapter = result.meta.get("framework_adapter") or self.framework_config.name
        result.meta.update(_framework_metadata(self.framework, adapter=adapter))
        result.meta.setdefault("framework_config", self.framework_config.inspect())
        if clean_input is not None:
            result.meta.setdefault("input", _json_like(clean_input))
        runtime_engine = self._runtime_engine_name()
        result.meta.setdefault(
            "requested_engine", self.metadata.get("requested_engine", runtime_engine)
        )
        result.meta.setdefault("runtime_engine", runtime_engine)
        result.meta.setdefault("execution_engine", self.engine)
        if result.engine == self.engine:
            result.engine = runtime_engine
        result = _coerce_output_data(result, self.output_contract)
        validation = result.validate(self.contract)
        return result.apply_validation(validation)

    def run_sync(
        self,
        input: Any = None,
        *,
        mode: str = "default",
        config: RunPolicy | dict[str, Any] | None = None,
    ) -> RunResult:
        """Alias for ``run`` for call sites that want explicit sync naming."""

        return self.run(input, mode=mode, config=config)

    def as_node(
        self,
        *,
        input: str | Callable[[dict[str, Any]], Any] = "prompt",
        output: str | Callable[[RunResult, dict[str, Any]], Any] | None = "answer",
        trace: str | None = "ada_trace",
        result_key: str | None = None,
        mode: str = "default",
        config: RunPolicy | dict[str, Any] | None = None,
    ):
        """Return a framework-neutral sync state-node callable."""

        def _node(state: dict[str, Any]) -> Any:
            prompt = _read_node_input(state, input)
            result = self.run(prompt, mode=mode, config=config)
            return _map_node_output(result, state, output, trace, result_key)

        return _node

    def as_async_node(
        self,
        *,
        input: str | Callable[[dict[str, Any]], Any] = "prompt",
        output: str | Callable[[RunResult, dict[str, Any]], Any] | None = "answer",
        trace: str | None = "ada_trace",
        result_key: str | None = None,
        mode: str = "default",
        config: RunPolicy | dict[str, Any] | None = None,
    ):
        """Return a framework-neutral async state-node callable."""

        async def _node(state: dict[str, Any]) -> Any:
            prompt = _read_node_input(state, input)
            result = await self.arun(prompt, mode=mode, config=config)
            return _map_node_output(result, state, output, trace, result_key)

        return _node

    def as_tool(self, *, name: str | None = None, description: str | None = None):
        tool_name = name or self.name

        def _agent_tool(prompt: str) -> dict[str, Any]:
            """Run this agent as a dict-returning tool."""

            result = self.run(prompt)
            return {
                "text": result.text,
                "data": result.data,
                "ok": result.ok,
                "trace": result.trace("compact"),
            }

        _agent_tool.__name__ = tool_name.replace(".", "_")
        _agent_tool.__doc__ = description or f"Run agent {self.name}."
        return _agent_tool

    def validate(self) -> ValidationResult:
        result = ValidationResult(ok=True)
        if self.engine == LANGGRAPH_ORCHESTRATOR:
            result.add(
                "langgraph_is_not_engine",
                "LangGraph is an orchestrator, not an AgenticSystem engine. Use agent.as_node(...) or agent.as_async_node(...).",
                path="agent.engine",
            )

        counts = Counter(self.tools)
        for tool_name in sorted(name for name, count in counts.items() if count > 1):
            result.add(
                "duplicate_agent_tool",
                f"Agent '{self.name}' references duplicate tool '{tool_name}'.",
                path="agent.tools",
                meta={"tool_name": tool_name, "count": counts[tool_name]},
            )

        for index, tool in enumerate(self._direct_tools):
            tool_validation = tool.check()
            for issue in tool_validation.issues:
                result.add(
                    issue.code,
                    issue.message,
                    severity=issue.severity,
                    path=f"agent.tools[{index}].{issue.path}"
                    if issue.path
                    else f"agent.tools[{index}]",
                    meta={"tool_name": tool.name, **issue.meta},
                )

        available = set(self.tools)
        if self.system is not None:
            system_tools = set(self.system.tool_names)
            available |= system_tools
            for name in self.tools:
                if name not in system_tools and name not in {
                    tool.name for tool in self._direct_tools
                }:
                    result.add(
                        "unknown_agent_tool",
                        f"Agent '{self.name}' references unknown tool '{name}'.",
                        path="agent.tools",
                        meta={"available_tools": sorted(system_tools)},
                    )

        for name in self.contract.must_call + self.contract.must_not_call:
            if name not in available:
                result.add(
                    "contract_references_unknown_tool",
                    f"Contract for agent '{self.name}' references unknown tool '{name}'.",
                    path="agent.contract",
                    meta={"available_tools": sorted(available)},
                )

        static_validation = validate_contract_policy(
            self.contract,
            self.policy,
            available_tools=available,
        )
        for issue in static_validation.issues:
            if issue.code == "contract_references_unknown_tool":
                # Keep the historical, agent-specific error above for backwards compatibility.
                continue
            result.add(
                issue.code,
                issue.message,
                severity=issue.severity,
                path=f"agent.{issue.path}" if issue.path else "agent.contract_policy",
                meta=issue.meta,
            )
        return result

    def eval(self, cases: list[dict[str, Any]], **kwargs: Any):
        if self.system is None:
            raise RuntimeError(
                "Direct Agent.eval(...) needs an attached AgenticSystem. Use `agent.bind(system)` first."
            )
        return self.system.eval(self, cases, **kwargs)


def _normalize_agent_tool_inputs(
    items: Any,
) -> tuple[tuple[str, ...], tuple[Tool, ...]]:
    """Normalize direct agent tool inputs into names and concrete Tool objects."""

    if items is None:
        return (), ()
    if isinstance(items, Tool):
        return (items.name,), (items,)
    if isinstance(items, Toolkit):
        return items.tool_names, ()
    if isinstance(items, str):
        return (items,), ()
    if callable(items):
        tool = Tool(name=getattr(items, "__name__", ""), function=items)
        return (tool.name,), (tool,)
    if isinstance(items, Iterable) and not isinstance(items, (str, bytes, dict)):
        names: list[str] = []
        tools: list[Tool] = []
        for item in items:
            item_names, item_tools = _normalize_agent_tool_inputs(item)
            names.extend(item_names)
            tools.extend(item_tools)
        return tuple(names), tuple(tools)
    try:
        return expand_tool_inputs(items), ()
    except TypeError as exc:
        raise TypeError(f"Unsupported agent tools value: {items!r}") from exc


def _normalize_agent_skill_inputs(
    items: Any,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[Tool, ...], tuple[Skill, ...]]:
    """Normalize runtime/loaded skills for direct Agent construction."""

    if items is None:
        return (), (), (), ()
    if isinstance(items, Skill):
        return items.tool_names, (items.name,), tuple(items.available_tools()), (items,)
    if isinstance(items, LoadedSkill):
        runtime_skill = getattr(items, "runtime_skill", None)
        if isinstance(runtime_skill, Skill):
            return (
                runtime_skill.tool_names,
                (runtime_skill.name,),
                tuple(runtime_skill.available_tools()),
                (runtime_skill,),
            )
        return tuple(items.manifest.tools), (items.manifest.name,), (), ()
    if isinstance(items, str):
        return (), (items,), (), ()
    if isinstance(items, Iterable) and not isinstance(items, (str, bytes, dict)):
        tool_names: list[str] = []
        skill_names: list[str] = []
        tools: list[Tool] = []
        skills: list[Skill] = []
        for item in items:
            item_tool_names, item_skill_names, item_tools, item_skills = (
                _normalize_agent_skill_inputs(item)
            )
            tool_names.extend(item_tool_names)
            skill_names.extend(item_skill_names)
            tools.extend(item_tools)
            skills.extend(item_skills)
        return tuple(tool_names), tuple(skill_names), tuple(tools), tuple(skills)
    raise TypeError(f"Unsupported agent skills value: {items!r}")


def _dedupe_preserve_order(values: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value)
        if text not in seen:
            out.append(text)
            seen.add(text)
    return tuple(out)


def _dedupe_tools(tools: Iterable[Tool]) -> tuple[Tool, ...]:
    out: list[Tool] = []
    seen: set[str] = set()
    for tool in tools:
        if tool.name not in seen:
            out.append(tool)
            seen.add(tool.name)
    return tuple(out)


def _dedupe_skills(skills: Iterable[Skill]) -> tuple[Skill, ...]:
    out: list[Skill] = []
    seen: set[str] = set()
    for skill in skills:
        if skill.name not in seen:
            out.append(skill)
            seen.add(skill.name)
    return tuple(out)


def _json_like(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _json_like(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_like(item) for item in value]
    if isinstance(value, type):
        return value.__name__
    return value


def _contract_name(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "__name__", type(value).__name__)


def _read_node_input(
    state: dict[str, Any], input: str | Callable[[dict[str, Any]], Any]
) -> Any:
    if callable(input):
        return input(state)
    if input not in state:
        raise GraphContractError(
            f"input key '{input}' not found in state. Available keys: {sorted(state.keys())}. "
            "Fix: pass input='<existing_key>' or input=lambda state: ..."
        )
    return state[input]


def _map_node_output(
    result: RunResult,
    state: dict[str, Any],
    output: str | Callable[[RunResult, dict[str, Any]], Any] | None,
    trace: str | None,
    result_key: str | None,
) -> Any:
    if callable(output):
        return output(result, state)

    update: dict[str, Any] = {}
    if output is not None:
        update[output] = result.text
    if result_key is not None:
        update[result_key] = result.to_dict()
    if trace is not None:
        update[trace] = result.trace("compact")
    return update
