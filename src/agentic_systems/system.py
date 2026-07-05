"""Agentic Systems public factory."""

from __future__ import annotations

import inspect
import os
from functools import wraps
from typing import Any, Callable, get_args, get_origin, get_type_hints

from .core.runtime import RuntimeConfig
from .providers.base import RuntimeToolSpec, ToolRegistryRuntime
from .engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    LANGGRAPH_ORCHESTRATOR,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_DIRECT_ENGINE,
    VLLM_RUNTIME_ENGINE,
    canonical_engine_name,
    supported_engine_names,
)
from .agents import Agent, _normalize_agent_tool_inputs
from .contracts import AgentContract, RunPolicy, ValidationResult
from .engines.bedrock import BedrockEngine
from .providers.openai_runtime import OpenAIRuntimeProvider
from .providers.vllm_runtime import VLLMRuntimeProvider
from .providers.python_direct import PythonDirectEngine
from .errors import ToolContractError
from .evals import run_eval
from .environments import AgenticEnvironment
from .integrations.langgraph import AgenticGraph
from .skills import LoadedSkill, Skill, load_skill
from .tools import Tool
from .tools.compat import Toolkit, assert_dict_tool_output


class PublicToolRegistry:
    """Read-only user-friendly view of tools registered through ``system.tool``.

    It supports dictionary-style lookup (``registry["sumar"]``), membership
    checks by name (``"sumar" in registry``), and direct iteration over Tool
    objects (``for tool in registry``). That last behavior prevents the common
    notebook mistake where users iterate over a plain dict and receive strings.
    """

    def __init__(self, tools: dict[str, Tool]) -> None:
        self._tools = dict(tools)

    def __getitem__(self, name: str) -> Tool:
        return self._tools[name]

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def keys(self):
        return self._tools.keys()

    def values(self):
        return self._tools.values()

    def items(self):
        return self._tools.items()

    def get(self, name: str, default=None):
        return self._tools.get(name, default)

    def to_dict(self) -> dict[str, Tool]:
        return dict(self._tools)

    def __repr__(self) -> str:
        return f"PublicToolRegistry({list(self._tools)!r})"


class InspectReport(dict):
    """Dictionary report with a convenience raise_if_errors method."""

    def raise_if_errors(self) -> "InspectReport":
        if not self.get("ok"):
            errors = self.get("errors", [])
            raise ValueError(f"Agentic Systems inspect failed: {errors}")
        return self


class AgenticSystem:
    """Canonical Agentic Systems system/factory for advanced use cases."""

    def __init__(
        self,
        *,
        model: str,
        region: str | None = None,
        defaults: dict[str, Any] | None = None,
        strict: bool = True,
        disable_framework_tracing: bool = True,
        runtime: RuntimeConfig | dict[str, Any] | None = None,
    ) -> None:
        os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
        self.runtime_config = RuntimeConfig.coerce(runtime) if runtime is not None else None
        self.model = model or (self.runtime_config.model_id if self.runtime_config else None)
        self.region = region or (self.runtime_config.region_name if self.runtime_config else None)
        self.defaults = defaults or {}
        self.strict = strict
        self._agents: list[Agent] = []
        self._toolkits: dict[str, Toolkit] = {}
        self._public_tools: dict[str, Tool] = {}
        self._skills: list[LoadedSkill] = []
        self._runtime_skills: dict[str, Skill] = {}
        self._engines: dict[str, Any] = {}
        max_tokens_default = self.defaults.get("max_tokens", 800)
        temperature_default = self.defaults.get("temperature", 0.0)
        if max_tokens_default is None:
            max_tokens_default = 800
        if temperature_default is None:
            temperature_default = 0.0

        self._disable_framework_tracing = disable_framework_tracing
        self._runtime = ToolRegistryRuntime(
            model_id=self.model,
            region_name=self.region,
            max_tokens_default=int(max_tokens_default),
            temperature_default=float(temperature_default),
        )
        self.region = self._runtime.region_name

    @property
    def tools(self):
        return self._runtime.tools

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self._runtime.tools)

    @property
    def public_tools(self) -> PublicToolRegistry:
        """Return a read-only Tool registry registered through ``system.tool``.

        Supports ``system.public_tools["name"]`` and direct iteration over
        Tool objects. Use ``system.public_tool_names`` when only names are
        needed.
        """

        return PublicToolRegistry(self._public_tools)

    @property
    def public_tool_names(self) -> tuple[str, ...]:
        """Return names of public Tool wrappers registered through ``system.tool``."""

        return tuple(self._public_tools)

    @property
    def agents(self) -> tuple[Agent, ...]:
        return tuple(self._agents)

    @property
    def skills(self) -> tuple[LoadedSkill, ...]:
        """Return filesystem-loaded skills.

        Runtime ``Skill(...)`` objects registered with ``system.skill(...)`` are
        exposed separately through ``system.runtime_skills`` so filesystem assets that
        expose ``LoadedSkill`` objects keep working unchanged.
        """

        return tuple(self._skills)

    @property
    def runtime_skills(self) -> tuple[Skill, ...]:
        """Return runtime ``Skill`` capabilities registered in this system."""

        return tuple(self._runtime_skills.values())

    @property
    def skill_names(self) -> tuple[str, ...]:
        """Return names of both runtime and filesystem-loaded skills."""

        names = [*self._runtime_skills.keys(), *(skill.manifest.name for skill in self._skills)]
        return _dedupe_preserve_order(names)

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ):
        """Register a dict-returning tool.

        In strict mode, both the return annotation and runtime value must be dict.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or fn.__name__
            if self.strict:
                _validate_tool_signature(tool_name, fn)

            public_tool = Tool(
                name=tool_name,
                description=description,
                function=fn,
                strict=self.strict,
            )
            self._public_tools[tool_name] = public_tool

            @wraps(fn)
            def _wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
                value = fn(*args, **kwargs)
                if self.strict:
                    return assert_dict_tool_output(tool_name, value)
                return value

            registered = self._runtime.tool(_wrapped, name=tool_name, description=public_tool.description or description)
            return fn if registered is _wrapped else registered

        if func is None:
            return decorator
        return decorator(func)

    def toolkit(self, name: str) -> Toolkit:
        toolkit = self._toolkits.get(name)
        if toolkit is None:
            toolkit = Toolkit(self, name)
            self._toolkits[name] = toolkit
        return toolkit

    def skill(self, skill: Skill) -> Skill:
        """Register a runtime ``Skill`` and its tools in this system.

        This is the bridge between the new user-facing ``Skill(...)`` object and
        the Bedrock-backed runtime registry. Registering the same skill
        twice is idempotent for tools with the same names.
        """

        if not isinstance(skill, Skill):
            raise TypeError("system.skill(...) expects a runtime Skill instance.")
        skill.check().raise_if_failed()
        for public_tool in skill.available_tools():
            self._register_tool_object(public_tool)
        self._runtime_skills[skill.name] = skill
        return skill

    def _register_tool_object(self, public_tool: Tool) -> Tool:
        """Register a public ``Tool`` object into the runtime registry.

        ``Tool`` is the source of truth for Pydantic input/output contracts.
        Runtime bridges such as Bedrock, LangGraph and OpenAI Agents receive the
        same neutral schema instead of rebuilding different contracts from a
        wrapper function signature.
        """

        if not isinstance(public_tool, Tool):
            raise TypeError(f"Expected Tool, got {type(public_tool).__name__}.")
        public_tool.check().raise_if_failed()
        if public_tool.function is None:
            raise ToolContractError(f"Tool '{public_tool.name}' has no callable function.")

        self._public_tools[public_tool.name] = public_tool

        @wraps(public_tool.function)
        def _wrapped(**kwargs: Any) -> dict[str, Any]:
            result = public_tool.run(kwargs)
            if not result.ok:
                error = result.data or {"message": result.text}
                raise ToolContractError(str(error.get("message") or error))
            return result.data

        if public_tool.input_schema is None:
            self._runtime.tool(_wrapped, name=public_tool.name, description=public_tool.description)
            return public_tool

        input_model = public_tool.input_schema
        input_schema = input_model.model_json_schema()
        input_schema.setdefault("type", "object")
        input_schema.setdefault("properties", {})
        input_schema.setdefault("additionalProperties", False)
        self._runtime._tools[public_tool.name] = RuntimeToolSpec(
            name=public_tool.name,
            description=public_tool.description or f"Tool {public_tool.name}",
            func=_wrapped,
            signature=inspect.signature(_wrapped),
            input_model=input_model,
            input_schema=input_schema,
            is_async=inspect.iscoroutinefunction(public_tool.function),
        )
        return public_tool

    def agent(
        self,
        *,
        name: str,
        instructions: str,
        tools: Any = None,
        skill: Any = None,
        skills: Any = None,
        engine: str = BEDROCK_RUNTIME_ENGINE,
        framework: str | None = None,
        input: Any = None,
        output: Any = None,
        contract: AgentContract | dict[str, Any] | None = None,
        policy: RunPolicy | dict[str, Any] | None = None,
        model: str | None = None,
        defaults: dict[str, Any] | None = None,
        runtime: RuntimeConfig | dict[str, Any] | None = None,
    ) -> Agent:
        runtime_config = RuntimeConfig.coerce(runtime) if runtime is not None else self.runtime_config
        if runtime_config is not None and engine == BEDROCK_RUNTIME_ENGINE:
            engine = runtime_config.provider
        engine = canonical_engine_name(engine)
        if engine == LANGGRAPH_ORCHESTRATOR:
            raise ValueError("LangGraph is an orchestrator, not an engine. Use agent.as_node(...).")
        skill_tool_names, skill_names = self._expand_skill_inputs(_merge_skill_inputs(skill, skills))
        explicit_tool_names, explicit_tool_objects = _normalize_agent_tool_inputs(tools)
        for public_tool in explicit_tool_objects:
            self._register_tool_object(public_tool)
        tool_names = _dedupe_preserve_order([*skill_tool_names, *explicit_tool_names])
        missing = [tool for tool in tool_names if tool not in self.tool_names]
        if missing:
            raise KeyError(f"Unknown tools requested for agent '{name}': {missing}. Available: {list(self.tool_names)}")
        agent = Agent(
            system=self,
            name=name,
            instructions=instructions,
            tools=tool_names,
            skills=skill_names,
            engine=engine,
            framework=framework,
            model=model or self.model,
            contract=contract,
            policy=policy,
            input_contract=input,
            output_contract=output,
            defaults=defaults,
            runtime=runtime_config,
        )
        self._agents.append(agent)
        return agent

    def _expand_skill_inputs(self, skills: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Register/expand runtime and filesystem skill references for an agent."""

        if skills is None:
            return (), ()
        if isinstance(skills, Skill):
            self.skill(skills)
            return skills.tool_names, (skills.name,)
        if isinstance(skills, LoadedSkill):
            runtime_skill = getattr(skills, "runtime_skill", None)
            if isinstance(runtime_skill, Skill):
                self.skill(runtime_skill)
            return tuple(skills.manifest.tools), (skills.manifest.name,)
        if isinstance(skills, str):
            if skills in self._runtime_skills:
                skill = self._runtime_skills[skills]
                return skill.tool_names, (skill.name,)
            for loaded in self._skills:
                if loaded.manifest.name == skills:
                    return tuple(loaded.manifest.tools), (loaded.manifest.name,)
            raise KeyError(f"Unknown skill '{skills}'. Available skills: {self.skill_names}")
        if isinstance(skills, (list, tuple, set, frozenset)):
            tool_names: list[str] = []
            skill_names: list[str] = []
            for item in skills:
                item_tool_names, item_skill_names = self._expand_skill_inputs(item)
                tool_names.extend(item_tool_names)
                skill_names.extend(item_skill_names)
            return _dedupe_preserve_order(tool_names), _dedupe_preserve_order(skill_names)
        raise TypeError(f"Unsupported skills value: {skills!r}")

    def graph(self, *, name: str, state: Any = None) -> AgenticGraph:
        return AgenticGraph(name=name, state=state)

    def load_skill(self, path: str) -> LoadedSkill:
        return load_skill(self, path)

    def inspect(self) -> InspectReport:
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        registry = self._runtime.validate_tool_registry()
        for issue in registry.get("issues", []):
            warnings.append({"source": "runtime_registry", **issue})
        for spec in self._runtime.tools:
            if self.strict and not _return_annotation_is_dict(spec.func):
                errors.append({"tool": spec.name, "issue": "tool_return_annotation_must_be_dict"})
        for agent in self._agents:
            validation = agent.validate()
            for issue in validation.issues:
                target = errors if issue.severity == "error" else warnings
                target.append(issue.model_dump(mode="json"))
        report = InspectReport(
            ok=not errors,
            model=self.model,
            region=self.region,
            strict=self.strict,
            tool_count=len(self.tools),
            tools=list(self.tool_names),
            agent_count=len(self._agents),
            agents=[agent.name for agent in self._agents],
            toolkit_count=len(self._toolkits),
            toolkits={name: list(toolkit.tool_names) for name, toolkit in self._toolkits.items()},
            skill_count=len(self._skills) + len(self._runtime_skills),
            skills=[skill.manifest.model_dump(mode="json") for skill in self._skills],
            runtime_skill_count=len(self._runtime_skills),
            runtime_skills=[skill.info() for skill in self._runtime_skills.values()],
            warnings=warnings,
            errors=errors,
        )
        return report

    def eval(self, agent: Agent, cases: list[dict[str, Any]], **kwargs: Any):
        return run_eval(agent, cases, **kwargs)

    def environment(self, records: Any, *, graph: Any, **kwargs: Any) -> AgenticEnvironment:
        """Create a Gymnasium-shaped episodic environment backed by a graph."""

        return AgenticEnvironment(records=records, graph=graph, **kwargs)

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any] | None = None):
        return self._runtime.execute_tool(tool_name, tool_input or {})

    def export_tool_specs(self, tool_names: list[str] | None = None):
        return self._runtime.export_tool_specs(tool_names)

    def _ensure_bedrock_runtime(self):
        """Hydrate the optional Bedrock provider only when a Bedrock path is used."""

        if hasattr(self._runtime, "run_direct"):
            return self._runtime
        try:
            from .providers.bedrock_runtime import BedrockRuntime
        except Exception as exc:  # pragma: no cover - depends on optional install
            raise ImportError(
                "Bedrock Runtime provider requires optional AWS dependencies. "
                "Install with: pip install -e '.[bedrock]'."
            ) from exc
        previous_runtime = self._runtime
        runtime = BedrockRuntime(
            model_id=self.model,
            region_name=self.region,
            max_tokens_default=getattr(previous_runtime, "max_tokens_default", 800),
            temperature_default=getattr(previous_runtime, "temperature_default", 0.0),
            disable_openai_runtime_tracing=self._disable_framework_tracing,
        )
        runtime._tools.update(getattr(previous_runtime, "_tools", {}))
        if hasattr(previous_runtime, "runtime"):
            runtime.runtime = previous_runtime.runtime
        if hasattr(previous_runtime, "bedrock"):
            runtime.bedrock = previous_runtime.bedrock
        if hasattr(previous_runtime, "sts"):
            runtime.sts = previous_runtime.sts
        self._runtime = runtime
        self.region = self._runtime.region_name
        return self._runtime

    def _engine(self, name: str):
        name = canonical_engine_name(name)
        if name == "auto":
            name = _resolve_auto_provider(self.model, self.region)
        if name == BEDROCK_RUNTIME_ENGINE and name not in self._engines and "bedrock" in self._engines:
            # Safe relocation for code that injected the old Bedrock key before
            # bedrock-runtime became the canonical engine name.
            self._engines[name] = self._engines["bedrock"]
        if name not in self._engines:
            if name == BEDROCK_RUNTIME_ENGINE:
                self._ensure_bedrock_runtime()
                self._engines[name] = BedrockEngine(self)
            elif name == OPENAI_RUNTIME_ENGINE:
                self._engines[name] = OpenAIRuntimeProvider(self)
            elif name == PYTHON_DIRECT_ENGINE:
                self._engines[name] = PythonDirectEngine(self)
            elif name == VLLM_RUNTIME_ENGINE:
                self._engines[name] = VLLMRuntimeProvider(self)
            else:
                raise ValueError(f"Unknown engine {name!r}. Supported engines: {list(supported_engine_names())}")
        return self._engines[name]


def _resolve_auto_provider(model: str | None, region: str | None) -> str:
    """Resolve ``provider='auto'`` to a concrete runtime backend.

    Priority:
    1. OpenAI when an API key or base URL is configured and the SDK is importable.
    2. Bedrock when AWS credentials/region are configured and the provider is importable.
    3. Fail explicitly if no supported backend is detectable.
    """

    if _openai_signal_present():
        try:
            from .providers.openai_runtime import OpenAIRuntimeProvider  # noqa: F401
        except Exception:
            pass
        else:
            return OPENAI_RUNTIME_ENGINE

    if _bedrock_signal_present(region):
        try:
            from .providers.bedrock_runtime import BedrockRuntime  # noqa: F401
        except Exception:
            pass
        else:
            return BEDROCK_RUNTIME_ENGINE

    raise ValueError(
        "provider='auto' could not resolve a backend. "
        "Set OPENAI_API_KEY for openai-runtime or AWS credentials/region for bedrock-runtime."
    )


def _openai_signal_present() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_ORG_ID")
        or os.getenv("OPENAI_PROJECT")
    )


def _bedrock_signal_present(region: str | None) -> bool:
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_SECRET_ACCESS_KEY")
        or os.getenv("AWS_SESSION_TOKEN")
        or os.getenv("AWS_PROFILE")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or region
    )



def _merge_skill_inputs(skill: Any = None, skills: Any = None) -> Any:
    if skill is None:
        return skills
    if skills is None:
        return [skill]
    if isinstance(skills, (list, tuple, set, frozenset)):
        return [skill, *list(skills)]
    return [skill, skills]


def _dedupe_preserve_order(values: Any) -> tuple[str, ...]:
    """Return unique string values while preserving first-seen order."""

    out: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value)
        if text not in seen:
            out.append(text)
            seen.add(text)
    return tuple(out)


def _validate_tool_signature(tool_name: str, fn: Callable[..., Any]) -> None:
    signature = inspect.signature(fn)
    for param_name, param in signature.parameters.items():
        if param.annotation is inspect.Signature.empty:
            raise ToolContractError(
                f"Tool '{tool_name}' parameter '{param_name}' is missing a type annotation. "
                "Fix: add explicit JSON-friendly annotations."
            )
    if not _return_annotation_is_dict(fn):
        raise ToolContractError(
            f"Tool '{tool_name}' must be annotated as returning dict. "
            "Fix: use `-> dict` and return {'key': value}."
        )


def _return_annotation_is_dict(fn: Callable[..., Any]) -> bool:
    try:
        hints = get_type_hints(fn)
        annotation = hints.get("return", inspect.signature(fn).return_annotation)
    except Exception:
        annotation = inspect.signature(fn).return_annotation
    if annotation is inspect.Signature.empty:
        return False
    if annotation in {dict, dict[str, Any]}:
        return True
    origin = get_origin(annotation)
    if origin is dict:
        return True
    # typing.Dict from older annotations also has dict origin in modern Python.
    return False
