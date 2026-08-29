"""Top-level ergonomic factories for Agentic Systems."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

from pydantic import SecretStr

from .agents import Agent
from .core.runtime import (
    RuntimeConfig,
    _load_dotenv,
    normalize_provider_priority,
    resolve_auto_provider,
)
from .core.scheduler import SchedulerConfig
from .core.provider import ModelProviderConfig
from .defaults import (
    DEFAULT_AWS_REGION,
    DEFAULT_BEDROCK_MODEL_ID,
    DEFAULT_OPENAI_MODEL_ID,
    DEFAULT_OLLAMA_MODEL_ID,
    DEFAULT_VLLM_MODEL_ID,
)
from .engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OLLAMA_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
    canonical_engine_name,
)
from .final_answer import output_schema as make_output_schema
from .integrations.config import FrameworkConfig
from .environments import AgenticEnvironment
from .evals import Evaluator
from .system import AgenticSystem
from .skills import Skill
from .skills.loader import load_skill_definition
from .tools import ToolSet
from .schemas.serving import ModelArtifact, VLLMServerSpec
from .serving.vllm import VLLMServer, vllm_server_spec
from .registry import provider_definition

DEFAULT_MODEL_ENV_VARS = provider_definition(BEDROCK_RUNTIME_ENGINE).model_env
OPENAI_MODEL_ENV_VARS = provider_definition(OPENAI_RUNTIME_ENGINE).model_env
OLLAMA_MODEL_ENV_VARS = provider_definition(OLLAMA_RUNTIME_ENGINE).model_env
VLLM_MODEL_ENV_VARS = provider_definition(VLLM_RUNTIME_ENGINE).model_env


def default_model_id() -> str:
    """Return the default Bedrock model id used by notebook-first examples."""

    _load_dotenv()
    for key in DEFAULT_MODEL_ENV_VARS:
        value = os.getenv(key)
        if value:
            return value
    return DEFAULT_BEDROCK_MODEL_ID


def default_openai_model_id() -> str:
    """Return the default OpenAI model id from environment configuration."""

    _load_dotenv()
    for key in OPENAI_MODEL_ENV_VARS:
        value = os.getenv(key)
        if value:
            return value
    return DEFAULT_OPENAI_MODEL_ID


def default_ollama_model_id() -> str:
    """Return the default Ollama model id from environment configuration."""

    _load_dotenv()
    for key in OLLAMA_MODEL_ENV_VARS:
        value = os.getenv(key)
        if value:
            return value
    return DEFAULT_OLLAMA_MODEL_ID


def default_vllm_model_id() -> str:
    """Return the default vLLM model id from environment configuration."""

    _load_dotenv()
    for key in VLLM_MODEL_ENV_VARS:
        value = os.getenv(key)
        if value:
            return value
    return DEFAULT_VLLM_MODEL_ID


def default_region() -> str:
    """Return the default AWS region used by notebook-first examples."""

    _load_dotenv()
    return (
        os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_AWS_REGION
    )


def scheduler(
    *,
    timeout_s: float | None = 60.0,
    max_retries: int = 0,
    max_tool_calls: int | None = 5,
    max_turns: int | None = 6,
    max_concurrency: int = 1,
    backoff_s: float = 0.0,
) -> SchedulerConfig:
    """Create a notebook-friendly scheduler configuration.

    The returned object is declarative and can be passed to ``lab.runtime(...)``.
    """

    return SchedulerConfig(
        timeout_s=timeout_s,
        max_retries=max_retries,
        max_tool_calls=max_tool_calls,
        max_turns=max_turns,
        max_concurrency=max_concurrency,
        backoff_s=backoff_s,
    )


def framework(
    name: str,
    *,
    agent_kwargs: dict[str, Any] | None = None,
    run_kwargs: dict[str, Any] | None = None,
) -> FrameworkConfig:
    """Configure a real orchestration Framework with native SDK kwargs."""

    return FrameworkConfig(
        name=name, agent_kwargs=agent_kwargs or {}, run_kwargs=run_kwargs or {}
    )


def provider(
    name: str = "auto",
    *,
    model: str | None = None,
    model_id: str | None = None,
    region: str | None = None,
    region_name: str | None = None,
    endpoint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelProviderConfig:
    """Describe a model provider independently from its execution framework."""

    return ModelProviderConfig(
        name=name,
        model_id=model_id or model,
        region_name=region_name or region,
        endpoint=endpoint,
        metadata=metadata or {},
    )


def model_artifact(
    model: str,
    *,
    base_model: str | None = None,
    adapter_path: str | None = None,
    tokenizer: str | None = None,
    revision: str | None = None,
    quantization: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelArtifact:
    """Declare portable model identity and future fine-tuning provenance."""

    return ModelArtifact(
        model_id=model,
        base_model_id=base_model,
        adapter_path=adapter_path,
        tokenizer_id=tokenizer,
        revision=revision,
        quantization=quantization,
        metadata=metadata or {},
    )


def model_server(
    model: str | ModelArtifact | None = None,
    *,
    backend: str = "vllm",
    spec: VLLMServerSpec | None = None,
    **configuration: Any,
) -> VLLMServer:
    """Create an explicit model-server lifecycle adapter.

    Starting a server is never implicit; call start(), use running(), or enter
    the returned object as a context manager.
    """

    if backend != "vllm":
        raise ValueError(f"Unknown model-server backend {backend!r}; expected 'vllm'.")
    if spec is not None:
        if model is not None or configuration:
            raise ValueError("spec cannot be combined with model or configuration.")
        return VLLMServer(spec)
    if model is None:
        raise ValueError("model_server requires model or spec.")
    return VLLMServer(vllm_server_spec(model, **configuration))


def toolset(system: AgenticSystem, name: str) -> ToolSet:
    """Create a named ToolSet owned by an explicit AgenticSystem."""

    if not isinstance(system, AgenticSystem):
        raise TypeError("toolset(system, name) requires an AgenticSystem owner.")
    return system.toolset(name)


def runtime(
    *,
    provider: str | ModelProviderConfig = "bedrock-runtime",
    model: str | None = None,
    model_id: str | None = None,
    region: str | None = None,
    region_name: str | None = None,
    scheduler: SchedulerConfig | dict[str, Any] | None = None,
    endpoint: str | None = None,
    api_key: str | SecretStr | None = None,
    metadata: dict[str, Any] | None = None,
    provider_priority: Iterable[str] | str | None = None,
    allow_python_fallback: bool = False,
) -> RuntimeConfig:
    """Create a runtime/provider configuration for ``lab.agent(..., runtime=...)``.

    ``model``/``region`` are accepted as user-facing aliases for the internal
    ``model_id``/``region_name`` fields. ``provider_priority`` controls
    ``provider="auto"`` without requiring YAML or hidden global state.
    """

    if isinstance(provider, ModelProviderConfig):
        provider_config = provider
        provider = provider_config.name
        model_id = model_id or provider_config.model_id
        region_name = region_name or provider_config.region_name
        metadata = {
            **provider_config.metadata,
            **(metadata or {}),
            "model_provider": provider_config.to_dict(),
        }
        if provider_config.endpoint:
            endpoint = endpoint or provider_config.endpoint

    selected_provider = canonical_engine_name(provider)
    priority = normalize_provider_priority(
        provider_priority, allow_python_fallback=allow_python_fallback
    )
    selected_model = (
        model_id
        or model
        or _default_runtime_model(selected_provider, region_name or region, priority)
    )
    selected_region = (
        region_name or region or _default_runtime_region(selected_provider, priority)
    )
    merged_metadata = _runtime_metadata(
        selected_provider, metadata, selected_region, priority
    )

    return RuntimeConfig(
        provider=provider,
        model_id=selected_model,
        region_name=selected_region,
        endpoint=endpoint,
        api_key=api_key,
        scheduler=SchedulerConfig.coerce(scheduler),
        metadata=merged_metadata,
        provider_priority=priority,
        allow_python_fallback=allow_python_fallback,
    )


def _default_runtime_model(
    provider: str, region: str | None, provider_priority: Iterable[str] | None = None
) -> str | None:
    _load_dotenv()
    if provider == "auto":
        try:
            resolved = resolve_auto_provider(region, provider_priority)
        except ValueError:
            return None
    else:
        resolved = provider
    if resolved == VLLM_RUNTIME_ENGINE:
        return default_vllm_model_id()
    if resolved == OPENAI_RUNTIME_ENGINE:
        return default_openai_model_id()
    if resolved == OLLAMA_RUNTIME_ENGINE:
        return default_ollama_model_id()
    if resolved == BEDROCK_RUNTIME_ENGINE:
        return default_model_id()
    if resolved == PYTHON_RUNTIME_ENGINE:
        return PYTHON_RUNTIME_ENGINE
    return None


def _default_runtime_region(
    provider: str, provider_priority: Iterable[str] | None = None
) -> str | None:
    if provider == BEDROCK_RUNTIME_ENGINE:
        return default_region()
    if provider == "auto":
        try:
            resolved = resolve_auto_provider(None, provider_priority)
        except ValueError:
            return None
        if resolved == BEDROCK_RUNTIME_ENGINE:
            return default_region()
    return None


def _runtime_metadata(
    provider: str,
    metadata: dict[str, Any] | None,
    region: str | None,
    provider_priority: Iterable[str] | None = None,
) -> dict[str, Any]:
    _load_dotenv()
    merged = dict(metadata or {})
    resolved = None
    if provider == "auto":
        try:
            resolved = resolve_auto_provider(region, provider_priority)
        except ValueError:
            resolved = None
    else:
        resolved = provider
    if resolved == VLLM_RUNTIME_ENGINE:
        merged.setdefault(
            "vllm",
            {
                "base_url": os.getenv("VLLM_BASE_URL") or None,
                "base_url_configured": _vllm_signal_present(),
                "api_key_configured": bool(os.getenv("VLLM_API_KEY")),
                "model_env_vars": [
                    key for key in VLLM_MODEL_ENV_VARS if os.getenv(key)
                ],
            },
        )
    if resolved == OLLAMA_RUNTIME_ENGINE:
        merged.setdefault(
            "ollama",
            {
                "base_url": os.getenv("OLLAMA_BASE_URL") or None,
                "base_url_configured": bool(os.getenv("OLLAMA_BASE_URL")),
                "api_key_configured": bool(os.getenv("OLLAMA_API_KEY")),
                "model_env_vars": [
                    key for key in OLLAMA_MODEL_ENV_VARS if os.getenv(key)
                ],
            },
        )
    if resolved == OPENAI_RUNTIME_ENGINE:
        merged.setdefault(
            "openai",
            {
                "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
                "base_url": os.getenv("OPENAI_BASE_URL") or None,
                "model_env_vars": [
                    key for key in OPENAI_MODEL_ENV_VARS if os.getenv(key)
                ],
            },
        )
    if resolved == BEDROCK_RUNTIME_ENGINE:
        merged.setdefault(
            "bedrock",
            {
                "aws_region": os.getenv("AWS_REGION")
                or os.getenv("AWS_DEFAULT_REGION")
                or None,
                "aws_profile_configured": bool(os.getenv("AWS_PROFILE")),
                "bedrock_api_key_configured": bool(
                    os.getenv("AWS_BEARER_TOKEN_BEDROCK")
                ),
                "credentials_configured": bool(
                    os.getenv("AWS_BEARER_TOKEN_BEDROCK")
                    or os.getenv("AWS_ACCESS_KEY_ID")
                    or os.getenv("AWS_SECRET_ACCESS_KEY")
                    or os.getenv("AWS_SESSION_TOKEN")
                ),
            },
        )
    return merged


def _vllm_signal_present() -> bool:
    return bool(os.getenv("VLLM_BASE_URL"))


def _ollama_signal_present() -> bool:
    return bool(os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"))


def output_schema(
    fields: list[str] | tuple[str, ...] | None = None,
    *,
    many: bool = False,
    root_key: str | None = None,
    required: bool = False,
    aliases: dict[str, str] | None = None,
):
    """Create a final-answer schema for ``lab.agent(..., output=...)``.

    This schema controls ``result.final`` only.  It does not change runtime
    metadata, tool events, usage, validation or raw evidence stored elsewhere in
    ``RunResult``.
    """

    return make_output_schema(
        fields, many=many, root_key=root_key, required=required, aliases=aliases
    )


def skill(
    *,
    name: str,
    description: str = "",
    tools: Iterable[Any] | None = None,
    prompts: dict[str, Any] | None = None,
    contracts: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    version: str = "0.1.0",
) -> Skill:
    """Create a reusable Skill through the canonical toolkit grammar."""

    return Skill(
        name=name,
        description=description,
        tools=tools,
        prompts=prompts,
        contracts=contracts,
        policy=policy,
        metadata=metadata,
        version=version,
    )


def environment(records: Any, **kwargs: Any) -> AgenticEnvironment:
    """Create an episodic environment through the canonical toolkit API."""

    return AgenticEnvironment(records=records, **kwargs)


def eval() -> Evaluator:  # noqa: A001 - intentional public grammar term.
    """Create the evaluation facade used to verify agents over declared cases."""

    return Evaluator()


def system(
    *,
    model: str | None = None,
    region: str | None = None,
    defaults: dict[str, Any] | None = None,
    strict: bool = True,
    runtime: RuntimeConfig | dict[str, Any] | None = None,
) -> AgenticSystem:
    """Create a provider-agnostic system through the canonical toolkit API."""

    return AgenticSystem(
        model=model,
        region=region,
        defaults=defaults,
        strict=strict,
        runtime=runtime,
    )


def load_skill(name_or_path: Any, **kwargs: Any) -> Any:
    """Load a runtime skill from a filesystem path or return an existing Skill.

    Recommended for tutorials and user projects:

    .. code-block:: python

        inspection = lab.load_skill("tutorials/skills/tutorial_api_inspection")

    The path is resolved relative to the current directory and its parents, so it
    works whether Jupyter starts in the repository root or inside a tutorial
    folder. Domain skills stay outside ``src/``; Agentic Systems only provides the
    loader/runtime contract.
    """

    if isinstance(name_or_path, Skill):
        return name_or_path

    text = str(name_or_path or "").strip()
    path = _resolve_skill_path(text)
    if path is not None:
        return load_skill_definition(path)

    raise ValueError(
        f"Unknown skill path {text!r}. Pass a Skill object or a valid filesystem skill directory "
        "containing SKILL.md and skill.py."
    )


def _resolve_skill_path(text: str) -> Path | None:
    """Resolve skill paths from repo root, notebook folders, or installed packages.

    Examples that should work after ``pip install -e .`` or ``pip install .``:

    - ``tutorials/skills/tutorial_api_inspection``
    - an absolute filesystem path
    """

    if not text:
        return None
    raw = Path(text).expanduser()
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        cwd = Path.cwd().resolve()
        for base in [cwd, *cwd.parents]:
            candidates.append(base / raw)
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

    packaged = _resolve_packaged_skill_path(text)
    if packaged is not None:
        return packaged
    return None


def _resolve_packaged_skill_path(text: str) -> Path | None:
    """Resolve slash-style package resources such as tutorials/foo/skill."""

    normalized = text.replace("\\", "/").strip("/")
    if not normalized:
        return None
    parts = [part for part in normalized.split("/") if part and part != "."]
    for index in range(len(parts), 0, -1):
        package = ".".join(parts[:index])
        remainder = parts[index:]
        try:
            traversable = resources.files(package)
        except (ModuleNotFoundError, ValueError, TypeError):
            continue
        for part in remainder:
            traversable = traversable / part
        try:
            candidate = Path(str(traversable))
        except TypeError:
            continue
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def agent(
    *,
    name: str,
    instructions: str = "",
    tools: Any = None,
    skill: Any = None,
    skills: Any = None,
    engine: str = "bedrock-runtime",
    framework: str | FrameworkConfig | None = None,
    model: str | None = None,
    region: str | None = None,
    input: Any = None,  # noqa: A002 - public ergonomic alias.
    output: Any = None,
    contract: Any = None,
    policy: Any = None,
    defaults: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    runtime: RuntimeConfig | dict[str, Any] | None = None,
) -> Agent:
    """Create an Agentic Systems agent without exposing a full system in notebooks.

    This is the recommended public entrypoint for fundamentals:

    .. code-block:: python

        agent = lab.agent(name="calculator", tools=[sumar])

    Internally it creates a small ``AgenticSystem`` and registers any
    concrete tools passed through ``tools=[...]``.  Users who need multiple
    shared agents, shared registry state, or environments may still create an
    system through ``lab.system(...)``.
    """

    resolved_skills = _merge_skill_inputs(skill, skills)
    runtime_config = RuntimeConfig.coerce(runtime) if runtime is not None else None
    effective_engine = (
        runtime_config.provider
        if runtime_config is not None
        else canonical_engine_name(engine)
    )
    effective_model = (
        model
        or (runtime_config.model_id if runtime_config else None)
        or _default_agent_model(effective_engine)
    )
    workspace = AgenticSystem(
        model=effective_model,
        region=region
        or (runtime_config.region_name if runtime_config else None)
        or default_region(),
        defaults=defaults,
        runtime=runtime_config,
    )
    created = workspace.agent(
        name=name,
        instructions=instructions,
        tools=tools,
        skills=resolved_skills,
        engine=effective_engine,
        framework=framework,
        input=input,
        output=output,
        contract=contract,
        policy=policy,
        model=effective_model,
        defaults=defaults,
    )
    if metadata:
        created.metadata.update(metadata)
    return created


def _merge_skill_inputs(skill: Any = None, skills: Any = None) -> Any:
    if skill is None:
        return skills
    if skills is None:
        return [skill]
    if isinstance(skills, (list, tuple, set, frozenset)):
        return [skill, *list(skills)]
    return [skill, skills]


def _default_agent_model(engine: str) -> str:
    if engine == PYTHON_RUNTIME_ENGINE:
        return "python-runtime"
    if engine == OPENAI_RUNTIME_ENGINE:
        return default_openai_model_id()
    if engine == OLLAMA_RUNTIME_ENGINE:
        return default_ollama_model_id()
    if engine == VLLM_RUNTIME_ENGINE:
        return default_vllm_model_id()
    return default_model_id()
