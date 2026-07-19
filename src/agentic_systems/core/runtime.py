"""Runtime configuration and provider registry exports."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from agentic_systems.engines.names import BEDROCK_RUNTIME_ENGINE, OPENAI_RUNTIME_ENGINE, PYTHON_RUNTIME_ENGINE, VLLM_RUNTIME_ENGINE, canonical_engine_name
from agentic_systems.providers.base import RuntimeToolSpec, ToolEnvelope, ToolRegistryRuntime
from agentic_systems.core.scheduler import DEFAULT_SCHEDULER_CONFIG, SchedulerConfig


DEFAULT_AUTO_PROVIDER_PRIORITY = (BEDROCK_RUNTIME_ENGINE, OPENAI_RUNTIME_ENGINE, VLLM_RUNTIME_ENGINE)
AUTO_PROVIDER_ENV_VAR = "AGENTIC_SYSTEMS_PROVIDER_PRIORITY"


@dataclass(frozen=True)
class RuntimeConfig:
    """Declarative runtime/provider selection for Agentic Systems execution."""

    provider: str = BEDROCK_RUNTIME_ENGINE
    model_id: str | None = None
    region_name: str | None = None
    scheduler: SchedulerConfig = field(default_factory=lambda: DEFAULT_SCHEDULER_CONFIG)
    metadata: dict[str, Any] = field(default_factory=dict)
    provider_priority: tuple[str, ...] | None = None
    allow_python_fallback: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", canonical_engine_name(self.provider))
        object.__setattr__(self, "scheduler", SchedulerConfig.coerce(self.scheduler))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))
        object.__setattr__(
            self,
            "provider_priority",
            normalize_provider_priority(self.provider_priority, allow_python_fallback=self.allow_python_fallback),
        )

    @classmethod
    def coerce(cls, value: "RuntimeConfig | dict[str, Any] | None", **overrides: Any) -> "RuntimeConfig":
        """Return a runtime config from an object, dict, or keyword overrides."""

        if isinstance(value, cls):
            base = value.to_dict()
        elif value is None:
            base = {}
        elif isinstance(value, dict):
            base = dict(value)
        else:
            raise TypeError("runtime must be a RuntimeConfig, dict, or None.")

        aliases = {
            "model": "model_id",
            "region": "region_name",
            "engine": "provider",
        }
        normalized: dict[str, Any] = {}
        for key, item in {**base, **overrides}.items():
            normalized[aliases.get(key, key)] = item
        if isinstance(normalized.get("scheduler"), dict):
            normalized["scheduler"] = SchedulerConfig.coerce(normalized["scheduler"])
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        payload = asdict(self)
        payload["scheduler"] = self.scheduler.to_dict()
        return payload

    def describe(self) -> dict[str, Any]:
        """Return a compact user-facing runtime summary for notebooks.

        For ``provider="auto"``, the summary performs a dry resolution from
        environment signals. It does not create SDK clients, execute models, or
        mutate the runtime object.
        """

        resolution = dict(self.metadata.get("resolution") or {})
        resolved = _describe_resolution(self.provider, self.region_name, resolution, self.provider_priority)
        return {
            "selected_provider": resolved["selected_provider"],
            "mode": resolved["mode"],
            "preferred_provider": resolved["preferred_provider"],
            "fallback_provider": resolved["fallback_provider"],
            "reason": resolved["reason"],
            "model": self.model_id,
            "region": self.region_name,
            "scheduler": self.scheduler.to_dict(),
            "provider_priority": list(resolved.get("provider_priority") or self.provider_priority or ()),
            "configuration": _safe_configuration(self.metadata),
        }


def _describe_resolution(provider: str, region: str | None, resolution: dict[str, Any], provider_priority: Iterable[str] | None = None) -> dict[str, Any]:
    _load_dotenv()
    priority = normalize_provider_priority(provider_priority)
    if resolution:
        return {
            "selected_provider": resolution.get("selected_provider") or provider,
            "mode": resolution.get("mode") or "explicit",
            "preferred_provider": resolution.get("preferred_provider"),
            "fallback_provider": resolution.get("fallback_provider"),
            "reason": resolution.get("reason") or "runtime configured explicitly",
            "provider_priority": tuple(resolution.get("provider_priority") or priority),
        }
    if provider != "auto":
        return {
            "selected_provider": provider,
            "mode": "explicit",
            "preferred_provider": None,
            "fallback_provider": None,
            "reason": "runtime configured explicitly",
            "provider_priority": priority,
        }

    available = _available_auto_providers(region, priority)
    if available:
        selected = available[0]
        return {
            "selected_provider": selected,
            "mode": "auto",
            "preferred_provider": selected,
            "fallback_provider": available[1] if len(available) > 1 else None,
            "reason": _auto_reason(selected),
            "provider_priority": priority,
        }
    return {
        "selected_provider": "auto",
        "mode": "auto-unresolved",
        "preferred_provider": None,
        "fallback_provider": None,
        "reason": _auto_unresolved_reason(priority),
        "provider_priority": priority,
    }


def normalize_provider_priority(priority: Iterable[str] | str | None, *, allow_python_fallback: bool = False) -> tuple[str, ...]:
    """Return canonical provider priority for ``provider='auto'``.

    Priority can be passed explicitly or through AGENTIC_SYSTEMS_PROVIDER_PRIORITY
    as a comma-separated list. ``python-runtime`` is allowed only when explicitly
    requested or when ``allow_python_fallback=True`` appends it.
    """

    _load_dotenv()
    raw_priority: Iterable[str] | str | None = priority
    if raw_priority is None:
        raw_priority = os.getenv(AUTO_PROVIDER_ENV_VAR)
    if raw_priority is None or raw_priority == "":
        values: list[str] = list(DEFAULT_AUTO_PROVIDER_PRIORITY)
    elif isinstance(raw_priority, str):
        values = [item.strip() for item in raw_priority.split(",") if item.strip()]
    else:
        values = [str(item).strip() for item in raw_priority if str(item).strip()]

    normalized: list[str] = []
    for value in values:
        provider = canonical_engine_name(value)
        if provider == "auto":
            raise ValueError("provider_priority cannot include 'auto'.")
        if provider not in normalized:
            normalized.append(provider)
    if allow_python_fallback and PYTHON_RUNTIME_ENGINE not in normalized:
        normalized.append(PYTHON_RUNTIME_ENGINE)
    return tuple(normalized)


def resolve_auto_provider(region: str | None, provider_priority: Iterable[str] | None = None) -> str:
    """Resolve ``provider='auto'`` to a concrete provider using priority order."""

    priority = normalize_provider_priority(provider_priority)
    available = _available_auto_providers(region, priority)
    if available:
        return available[0]
    raise ValueError(
        "provider='auto' could not resolve a backend. "
        f"Configured priority: {', '.join(priority)}. "
        "Set AWS credentials/region for bedrock-runtime, OPENAI_API_KEY for openai-runtime, "
        "VLLM_BASE_URL for vllm-runtime, or include python-runtime explicitly for deterministic fallback."
    )


def _available_auto_providers(region: str | None, priority: Iterable[str]) -> list[str]:
    available: list[str] = []
    for provider in priority:
        if _provider_available(provider, region):
            available.append(provider)
    return available


def _provider_available(provider: str, region: str | None) -> bool:
    if provider == BEDROCK_RUNTIME_ENGINE:
        return _bedrock_signal_present(region) and _module_available("boto3")
    if provider == OPENAI_RUNTIME_ENGINE:
        return _openai_signal_present() and _module_available("openai")
    if provider == VLLM_RUNTIME_ENGINE:
        return _vllm_signal_present() and _module_available("openai")
    if provider == PYTHON_RUNTIME_ENGINE:
        return True
    return False


def _auto_reason(provider: str) -> str:
    if provider == BEDROCK_RUNTIME_ENGINE:
        return "AWS credentials and region detected"
    if provider == OPENAI_RUNTIME_ENGINE:
        return "OPENAI_API_KEY/OPENAI config detected"
    if provider == VLLM_RUNTIME_ENGINE:
        return "VLLM_BASE_URL/vLLM config detected"
    if provider == PYTHON_RUNTIME_ENGINE:
        return "python-runtime deterministic fallback enabled"
    return "provider selected by configured priority"


def _auto_unresolved_reason(priority: Iterable[str]) -> str:
    hints = []
    for provider in priority:
        if provider == BEDROCK_RUNTIME_ENGINE:
            hints.append("AWS credentials and region")
        elif provider == OPENAI_RUNTIME_ENGINE:
            hints.append("OPENAI_API_KEY/OpenAI config")
        elif provider == VLLM_RUNTIME_ENGINE:
            hints.append("VLLM_BASE_URL/vLLM config")
        elif provider == PYTHON_RUNTIME_ENGINE:
            hints.append("python-runtime fallback")
    return "no " + ", ".join(hints) + " detected"

def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _load_dotenv(start: Path | None = None) -> bool:
    """Load a local .env file without overriding existing environment values."""

    root = _find_dotenv(start or Path.cwd())
    if root is None:
        return False
    for raw_line in root.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return True


def _find_dotenv(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        path = candidate / ".env"
        if path.exists() and path.is_file():
            return path
    return None


def _vllm_signal_present() -> bool:
    return bool(os.getenv("VLLM_BASE_URL"))


def _openai_signal_present() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_BASE_URL")
    )


def _aws_shared_credentials_present() -> bool:
    configured_path = os.getenv("AWS_SHARED_CREDENTIALS_FILE")
    credentials_path = Path(configured_path).expanduser() if configured_path else Path.home() / ".aws" / "credentials"
    return credentials_path.is_file()


def _bedrock_signal_present(region: str | None) -> bool:
    region_present = bool(region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
    static_credentials = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    profile_credentials = bool(os.getenv("AWS_PROFILE"))
    web_identity = bool(os.getenv("AWS_ROLE_ARN") and os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE"))
    container_credentials = bool(
        os.getenv("AWS_CONTAINER_CREDENTIALS_FULL_URI")
        or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
    )
    authentication_present = (
        static_credentials
        or profile_credentials
        or web_identity
        or container_credentials
        or _aws_shared_credentials_present()
    )
    return region_present and authentication_present


def _safe_configuration(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return runtime configuration metadata that is safe to print."""

    configuration: dict[str, Any] = {}
    for key in ("vllm", "openai", "bedrock"):
        value = metadata.get(key)
        if isinstance(value, dict):
            configuration[key] = dict(value)
    return configuration


__all__ = [
    "AUTO_PROVIDER_ENV_VAR",
    "DEFAULT_AUTO_PROVIDER_PRIORITY",
    "RuntimeConfig",
    "normalize_provider_priority",
    "resolve_auto_provider",
    "RuntimeToolSpec",
    "ToolEnvelope",
    "ToolRegistryRuntime",
]
