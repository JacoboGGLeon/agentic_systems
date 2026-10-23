"""Versioned contracts for explicitly managed model-serving processes."""

from __future__ import annotations

from typing import Literal

from pydantic import (
    Field,
    SecretStr,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)

from .base import JsonValue, PersistedSpec


SERVING_SCHEMA_VERSION = "agentic_systems.serving.v1"


class _ServingSpec(PersistedSpec):
    schema_version: str = SERVING_SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def supported_schema_version(cls, value: str) -> str:
        if value != SERVING_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported serving schema {value!r}; expected "
                f"{SERVING_SCHEMA_VERSION!r}."
            )
        return value


class ModelArtifact(_ServingSpec):
    """Portable identity and provenance for a model consumed by a server."""

    model_id: StrictStr
    base_model_id: StrictStr | None = None
    adapter_path: StrictStr | None = None
    tokenizer_id: StrictStr | None = None
    revision: StrictStr | None = None
    quantization: StrictStr | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class VLLMServerSpec(_ServingSpec):
    """Closed declaration for a local vLLM OpenAI-compatible server."""

    backend: Literal["vllm"] = "vllm"
    artifact: ModelArtifact
    profile: Literal["fast", "medium", "power", "custom"] = "fast"
    served_model_name: StrictStr | None = None
    host: StrictStr = "127.0.0.1"
    port: StrictInt = Field(default=8000, ge=1, le=65535)
    gpu_memory_utilization: StrictFloat = Field(default=0.4, gt=0, le=1)
    max_model_len: StrictInt = Field(default=2048, ge=1)
    max_num_seqs: StrictInt = Field(default=4, ge=1)
    enable_auto_tool_choice: StrictBool = True
    tool_call_parser: StrictStr | None = "hermes"
    reasoning_parser: StrictStr | None = None
    generation_config: StrictStr | None = "vllm"
    api_key: SecretStr = Field(default=SecretStr("vllm"), exclude=True, repr=False)
    startup_timeout_s: StrictFloat = Field(default=600.0, gt=0)
    log_path: StrictStr = "vllm-server.log"
    binary: StrictStr = "vllm"
    extra_args: tuple[StrictStr, ...] = ()


class EndpointInfo(_ServingSpec):
    """Non-secret endpoint identity returned by a managed model server."""

    backend: StrictStr
    base_url: StrictStr
    model_id: StrictStr
    api_key_configured: StrictBool = False
    pid: StrictInt | None = None
    owned: StrictBool = False


class ServerHealth(_ServingSpec):
    """Serializable health projection for local or external model servers."""

    status: Literal["starting", "healthy", "stopped", "failed", "timeout"]
    endpoint: EndpointInfo
    detail: StrictStr | None = None


__all__ = [
    "SERVING_SCHEMA_VERSION",
    "EndpointInfo",
    "ModelArtifact",
    "ServerHealth",
    "VLLMServerSpec",
]
