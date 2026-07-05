"""Top-level ergonomic factories for Agentic Systems."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path
from typing import Any

from .agents import Agent
from .core.runtime import RuntimeConfig, _bedrock_signal_present, _load_dotenv, _openai_signal_present
from .core.scheduler import SchedulerConfig
from .engines.names import BEDROCK_RUNTIME_ENGINE, OPENAI_RUNTIME_ENGINE, PYTHON_DIRECT_ENGINE, canonical_engine_name
from .final_answer import output_schema as make_output_schema
from .system import AgenticSystem
from .skills import Skill

DEFAULT_MODEL_ENV_VARS = (
    "AGENTIC_SYSTEMS_MODEL_ID",
    "OTC_MODEL_ID",
    "BEDROCK_MODEL_ID",
)

OPENAI_MODEL_ENV_VARS = (
    "AGENTIC_SYSTEMS_OPENAI_MODEL_ID",
    "OPENAI_MODEL_ID",
    "OPENAI_MODEL",
)


def default_model_id() -> str:
    """Return the default Bedrock model id used by notebook-first examples."""

    _load_dotenv()
    for key in DEFAULT_MODEL_ENV_VARS:
        value = os.getenv(key)
        if value:
            return value
    return "qwen.qwen3-32b-v1:0"


def default_openai_model_id() -> str:
    """Return the default OpenAI model id from environment configuration."""

    _load_dotenv()
    for key in OPENAI_MODEL_ENV_VARS:
        value = os.getenv(key)
        if value:
            return value
    return "gpt-4o-mini"


def default_region() -> str:
    """Return the default AWS region used by notebook-first examples."""

    _load_dotenv()
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"




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


def runtime(
    *,
    provider: str = "bedrock-runtime",
    model: str | None = None,
    model_id: str | None = None,
    region: str | None = None,
    region_name: str | None = None,
    scheduler: SchedulerConfig | dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RuntimeConfig:
    """Create a runtime/provider configuration for ``lab.agent(..., runtime=...)``.

    ``model``/``region`` are accepted as user-facing aliases for the internal
    ``model_id``/``region_name`` fields.
    """

    selected_provider = canonical_engine_name(provider)
    selected_model = model_id or model or _default_runtime_model(selected_provider, region_name or region)
    selected_region = region_name or region or _default_runtime_region(selected_provider)
    merged_metadata = _runtime_metadata(selected_provider, metadata, selected_region)

    return RuntimeConfig(
        provider=provider,
        model_id=selected_model,
        region_name=selected_region,
        scheduler=SchedulerConfig.coerce(scheduler),
        metadata=merged_metadata,
    )


def _default_runtime_model(provider: str, region: str | None) -> str | None:
    _load_dotenv()
    if provider == OPENAI_RUNTIME_ENGINE or (provider == "auto" and _openai_signal_present()):
        return default_openai_model_id()
    if provider == BEDROCK_RUNTIME_ENGINE or (provider == "auto" and _bedrock_signal_present(region)):
        return default_model_id()
    return None


def _default_runtime_region(provider: str) -> str | None:
    if provider == BEDROCK_RUNTIME_ENGINE or (provider == "auto" and not _openai_signal_present() and _bedrock_signal_present(None)):
        return default_region()
    return None


def _runtime_metadata(provider: str, metadata: dict[str, Any] | None, region: str | None) -> dict[str, Any]:
    _load_dotenv()
    merged = dict(metadata or {})
    if provider == OPENAI_RUNTIME_ENGINE or (provider == "auto" and _openai_signal_present()):
        merged.setdefault(
            "openai",
            {
                "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
                "base_url": os.getenv("OPENAI_BASE_URL") or None,
                "org_id_configured": bool(os.getenv("OPENAI_ORG_ID")),
                "project": os.getenv("OPENAI_PROJECT") or None,
                "model_env_vars": [key for key in OPENAI_MODEL_ENV_VARS if os.getenv(key)],
            },
        )
    if provider == BEDROCK_RUNTIME_ENGINE or (provider == "auto" and _bedrock_signal_present(region)):
        merged.setdefault(
            "bedrock",
            {
                "aws_region": os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None,
                "aws_profile_configured": bool(os.getenv("AWS_PROFILE")),
                "credentials_configured": bool(
                    os.getenv("AWS_ACCESS_KEY_ID")
                    or os.getenv("AWS_SECRET_ACCESS_KEY")
                    or os.getenv("AWS_SESSION_TOKEN")
                ),
            },
        )
    return merged


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

    return make_output_schema(fields, many=many, root_key=root_key, required=required, aliases=aliases)


def load_skill(name_or_path: Any, **kwargs: Any) -> Any:
    """Load a runtime skill from a filesystem path or return an existing Skill.

    Recommended for tutorials and user projects:

    .. code-block:: python

        accountability = lab.load_skill("tutorials/skills/accountability_otc")

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
        workspace = AgenticSystem(
            model=kwargs.pop("model", None) or default_model_id(),
            region=kwargs.pop("region", None) or default_region(),
            defaults=kwargs.pop("defaults", None),
        )
        loaded = workspace.load_skill(path)
        return loaded.runtime_skill if loaded.runtime_skill is not None else loaded

    raise ValueError(
        f"Unknown skill path {text!r}. Pass a Skill object or a valid filesystem skill directory "
        "containing SKILL.md and skill.py."
    )


def _resolve_skill_path(text: str) -> Path | None:
    """Resolve skill paths from repo root, notebook folders, or installed packages.

    Examples that should work after ``pip install -e .`` or ``pip install .``:

    - ``tutorials/skills/accountability_otc``
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

    normalized = text.replace('\\', '/').strip('/')
    if not normalized:
        return None
    parts = [part for part in normalized.split('/') if part and part != '.']
    for index in range(len(parts), 0, -1):
        package = '.'.join(parts[:index])
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
    framework: str | None = None,
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
    explicit ``lab.AgenticSystem(...)`` system.
    """

    resolved_skills = _merge_skill_inputs(skill, skills)
    runtime_config = RuntimeConfig.coerce(runtime) if runtime is not None else None
    effective_engine = runtime_config.provider if runtime_config is not None else canonical_engine_name(engine)
    effective_model = model or (runtime_config.model_id if runtime_config else None) or _default_agent_model(effective_engine)
    workspace = AgenticSystem(
        model=effective_model,
        region=region or (runtime_config.region_name if runtime_config else None) or default_region(),
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
    if engine == PYTHON_DIRECT_ENGINE:
        return "local-python"
    if engine == OPENAI_RUNTIME_ENGINE:
        return default_openai_model_id()
    return default_model_id()
