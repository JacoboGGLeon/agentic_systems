"""Canonical execution and provider configuration schemas."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import (
    Field,
    SecretStr,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

from .base import ContractModel, JsonValue


EXECUTION_SCHEMA_VERSION = "agentic_systems.execution.v1"


class ExecutionLimits(ContractModel):
    """Single source of truth for bounded execution semantics.

    ``max_tool_calls=None`` uses the caller default, zero forbids tools, and a
    positive value is the maximum number of calls permitted.
    """

    max_turns: StrictInt | None = Field(default=6, ge=1)
    max_tool_calls: StrictInt | None = Field(default=5, ge=0)
    max_tokens: StrictInt | None = Field(default=None, ge=1)
    timeout_s: StrictFloat | StrictInt | None = Field(default=60.0, gt=0)
    max_concurrency: StrictInt = Field(default=1, ge=1)
    max_retries: StrictInt = Field(default=0, ge=0)
    max_repairs: StrictInt = Field(default=0, ge=0)
    backoff_s: StrictFloat | StrictInt = Field(default=0.0, ge=0)


class ContractExecutionBudget(ContractModel):
    """Provider-agnostic budget derived from a tool-bearing contract.

    The budget reserves turns for deciding, invoking each required tool,
    finalizing the public answer, protocol overhead, and a safety margin.
    Explicit limits remain supported, but impossible configurations fail
    before an SDK or model is called.
    """

    required_tool_calls: StrictInt = Field(default=0, ge=0)
    decision_turns: StrictInt = Field(default=1, ge=1)
    finalization_turns: StrictInt = Field(default=1, ge=0)
    protocol_overhead_turns: StrictInt = Field(default=1, ge=0)
    safety_margin_turns: StrictInt = Field(default=1, ge=0)
    max_turns: StrictInt | None = Field(default=None, ge=1)
    max_tool_calls: StrictInt | None = Field(default=None, ge=0)

    @property
    def minimum_turns(self) -> int:
        return (
            self.decision_turns
            + self.required_tool_calls
            + self.finalization_turns
            + self.protocol_overhead_turns
            + self.safety_margin_turns
        )

    @property
    def effective_max_turns(self) -> int:
        return self.max_turns if self.max_turns is not None else self.minimum_turns

    @property
    def effective_max_tool_calls(self) -> int:
        return (
            self.max_tool_calls
            if self.max_tool_calls is not None
            else self.required_tool_calls
        )

    @model_validator(mode="after")
    def validate_budget(self) -> "ContractExecutionBudget":
        if self.max_turns is not None and self.max_turns < self.minimum_turns:
            raise ValueError(
                "max_turns is smaller than the contract-derived minimum "
                f"({self.max_turns} < {self.minimum_turns})"
            )
        if (
            self.max_tool_calls is not None
            and self.max_tool_calls < self.required_tool_calls
        ):
            raise ValueError(
                "max_tool_calls is smaller than required_tool_calls "
                f"({self.max_tool_calls} < {self.required_tool_calls})"
            )
        return self


class _RuntimeBase(ContractModel):
    model_id: StrictStr | None = None
    endpoint: StrictStr | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class PythonRuntimeSpec(_RuntimeBase):
    provider: Literal["python-runtime"] = "python-runtime"


class OpenAIRuntimeSpec(_RuntimeBase):
    provider: Literal["openai-runtime"] = "openai-runtime"
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)


class OllamaRuntimeSpec(_RuntimeBase):
    provider: Literal["ollama-runtime"] = "ollama-runtime"


class BedrockRuntimeSpec(_RuntimeBase):
    provider: Literal["bedrock-runtime"] = "bedrock-runtime"
    region_name: StrictStr | None = None
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)


class VLLMRuntimeSpec(_RuntimeBase):
    provider: Literal["vllm-runtime"] = "vllm-runtime"
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)


ProviderRuntimeSpec: TypeAlias = Annotated[
    PythonRuntimeSpec
    | OpenAIRuntimeSpec
    | OllamaRuntimeSpec
    | BedrockRuntimeSpec
    | VLLMRuntimeSpec,
    Field(discriminator="provider"),
]


RuntimeProviderName: TypeAlias = Literal[
    "auto",
    "python-runtime",
    "openai-runtime",
    "ollama-runtime",
    "bedrock-runtime",
    "vllm-runtime",
]


class RuntimeConfigSchema(ContractModel):
    """Compatibility schema used internally by the 2.0 RuntimeConfig facade."""

    provider: RuntimeProviderName = "bedrock-runtime"
    model_id: StrictStr | None = None
    region_name: StrictStr | None = None
    endpoint: StrictStr | None = None
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    provider_priority: tuple[StrictStr, ...] | None = None
    allow_python_fallback: StrictBool = False


__all__ = [
    "EXECUTION_SCHEMA_VERSION",
    "BedrockRuntimeSpec",
    "ContractExecutionBudget",
    "ExecutionLimits",
    "OllamaRuntimeSpec",
    "OpenAIRuntimeSpec",
    "ProviderRuntimeSpec",
    "PythonRuntimeSpec",
    "RuntimeConfigSchema",
    "RuntimeProviderName",
    "VLLMRuntimeSpec",
]
