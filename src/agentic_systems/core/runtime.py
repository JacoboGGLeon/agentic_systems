"""Runtime configuration and provider registry exports."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from dataclasses import asdict, dataclass, field
from typing import Any

from agentic_systems.engines.names import BEDROCK_RUNTIME_ENGINE, OPENAI_RUNTIME_ENGINE, canonical_engine_name
from agentic_systems.providers.base import RuntimeToolSpec, ToolEnvelope, ToolRegistryRuntime
from agentic_systems.core.scheduler import DEFAULT_SCHEDULER_CONFIG, SchedulerConfig


@dataclass(frozen=True)
class RuntimeConfig:
    """Declarative runtime/provider selection for Agentic Systems execution."""

    provider: str = BEDROCK_RUNTIME_ENGINE
    model_id: str | None = None
    region_name: str | None = None
    scheduler: SchedulerConfig = field(default_factory=lambda: DEFAULT_SCHEDULER_CONFIG)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", canonical_engine_name(self.provider))
        object.__setattr__(self, "scheduler", SchedulerConfig.coerce(self.scheduler))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

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
        resolved = _describe_resolution(self.provider, self.region_name, resolution)
        return {
            "selected_provider": resolved["selected_provider"],
            "mode": resolved["mode"],
            "preferred_provider": resolved["preferred_provider"],
            "fallback_provider": resolved["fallback_provider"],
            "reason": resolved["reason"],
            "model": self.model_id,
            "region": self.region_name,
            "scheduler": self.scheduler.to_dict(),
            "configuration": _safe_configuration(self.metadata),
        }


def _describe_resolution(provider: str, region: str | None, resolution: dict[str, Any]) -> dict[str, Any]:
    _load_dotenv()
    if resolution:
        return {
            "selected_provider": resolution.get("selected_provider") or provider,
            "mode": resolution.get("mode") or "explicit",
            "preferred_provider": resolution.get("preferred_provider"),
            "fallback_provider": resolution.get("fallback_provider"),
            "reason": resolution.get("reason") or "runtime configured explicitly",
        }
    if provider != "auto":
        return {
            "selected_provider": provider,
            "mode": "explicit",
            "preferred_provider": None,
            "fallback_provider": None,
            "reason": "runtime configured explicitly",
        }
    if _openai_signal_present() and _module_available("openai"):
        return {
            "selected_provider": OPENAI_RUNTIME_ENGINE,
            "mode": "auto",
            "preferred_provider": OPENAI_RUNTIME_ENGINE,
            "fallback_provider": BEDROCK_RUNTIME_ENGINE if _bedrock_signal_present(region) else None,
            "reason": "OPENAI_API_KEY/OPENAI config detected",
        }
    if _bedrock_signal_present(region) and _module_available("boto3"):
        return {
            "selected_provider": BEDROCK_RUNTIME_ENGINE,
            "mode": "auto",
            "preferred_provider": BEDROCK_RUNTIME_ENGINE,
            "fallback_provider": None,
            "reason": "AWS credentials/region detected",
        }
    return {
        "selected_provider": "auto",
        "mode": "auto-unresolved",
        "preferred_provider": None,
        "fallback_provider": None,
        "reason": "no OPENAI_API_KEY/OpenAI config or AWS credentials/region detected",
    }


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


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


def _safe_configuration(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return runtime configuration metadata that is safe to print."""

    configuration: dict[str, Any] = {}
    for key in ("openai", "bedrock"):
        value = metadata.get(key)
        if isinstance(value, dict):
            configuration[key] = dict(value)
    return configuration


__all__ = [
    "RuntimeConfig",
    "RuntimeToolSpec",
    "ToolEnvelope",
    "ToolRegistryRuntime",
]
