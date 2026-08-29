"""Canonical provider/framework compatibility and test-contract registry.

Every presentation layer consumes this module.  Runtime readiness remains a
separate concern: a declared compatible pair can still require a dependency,
credential, endpoint, model, or external attestation before live execution.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as distribution_version
from itertools import product
from typing import Literal
from .schemas.attestation import (
    LIVE_SCENARIO_NAMES,
    LiveScenarioName as ScenarioName,
)

from .schemas.base import ContractModel


REGISTRY_SCHEMA_VERSION = "agentic_systems.registry.v1"
LIVE_ATTESTATION_SCHEMA_VERSION = "agentic_systems.live-attestation.v1"

CapabilityStatus = Literal["required", "optional", "degraded", "unsupported"]


class CapabilitySpec(ContractModel):
    name: str
    status: CapabilityStatus
    detail: str = ""


class ProviderDefinition(ContractModel):
    name: str
    dependency: str | None = None
    extra: str | None = None
    credential_env: tuple[str, ...] = ()
    endpoint_env: tuple[str, ...] = ()
    model_env: tuple[str, ...] = ()
    capabilities: tuple[CapabilitySpec, ...]
    attestation_environment: tuple[str, ...] = ()
    requires_model_identity: bool = False
    live_flag: str | None = None
    authentication_modes: tuple[str, ...] = ()


class FrameworkDefinition(ContractModel):
    name: str
    dependency: str | None = None
    extra: str | None = None
    capabilities: tuple[CapabilitySpec, ...]
    policy_fields: tuple[str, ...] = ()


class MatrixContract(ContractModel):
    provider: str
    framework: str
    status: Literal["supported", "degraded", "unsupported"] = "supported"
    scenarios: tuple[ScenarioName, ...] = LIVE_SCENARIO_NAMES
    reason: str = ""


def _cap(name: str, status: CapabilityStatus, detail: str = "") -> CapabilitySpec:
    return CapabilitySpec(name=name, status=status, detail=detail)


_COMMON_PROVIDER_CAPABILITIES = (
    _cap("normalized_run_result", "required"),
    _cap("stable_runtime_identity", "required"),
    _cap("structured_failure", "required"),
    _cap("json_serialization", "required"),
)

PROVIDERS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        name="python-runtime",
        authentication_modes=("local",),
        capabilities=_COMMON_PROVIDER_CAPABILITIES
        + (
            _cap("deterministic_execution", "required"),
            _cap("model_generation", "unsupported"),
            _cap(
                "native_async", "degraded", "Async facade over deterministic execution."
            ),
        ),
    ),
    ProviderDefinition(
        name="bedrock-runtime",
        dependency="boto3",
        extra="bedrock",
        credential_env=(
            "AWS_BEARER_TOKEN_BEDROCK",
            "AWS_ACCESS_KEY_ID",
            "AWS_PROFILE",
            "AWS_ROLE_ARN",
        ),
        requires_model_identity=True,
        live_flag="RUN_BEDROCK_LIVE",
        authentication_modes=("bedrock-api-key", "aws-credential-chain"),
        endpoint_env=("AWS_REGION", "AWS_DEFAULT_REGION"),
        model_env=("BEDROCK_MODEL_ID",),
        capabilities=_COMMON_PROVIDER_CAPABILITIES
        + (_cap("model_generation", "required"), _cap("native_async", "degraded")),
    ),
    ProviderDefinition(
        name="openai-runtime",
        dependency="openai",
        requires_model_identity=True,
        live_flag="RUN_OPENAI_LIVE",
        authentication_modes=("api-key", "custom-endpoint"),
        extra="openai",
        credential_env=("OPENAI_API_KEY",),
        endpoint_env=("OPENAI_BASE_URL",),
        model_env=("OPENAI_MODEL",),
        capabilities=_COMMON_PROVIDER_CAPABILITIES
        + (_cap("model_generation", "required"), _cap("native_async", "required")),
    ),
    ProviderDefinition(
        name="vllm-runtime",
        dependency="openai",
        attestation_environment=("cuda", "gpu", "vllm"),
        requires_model_identity=True,
        live_flag="RUN_VLLM_LIVE",
        authentication_modes=("openai-compatible",),
        extra="vllm-client",
        endpoint_env=("VLLM_BASE_URL",),
        model_env=("VLLM_MODEL",),
        capabilities=_COMMON_PROVIDER_CAPABILITIES
        + (_cap("model_generation", "required"), _cap("native_async", "required")),
    ),
    ProviderDefinition(
        name="ollama-runtime",
        dependency="openai",
        extra="openai",
        requires_model_identity=True,
        live_flag="RUN_OLLAMA_LIVE",
        authentication_modes=("local-openai-compatible",),
        endpoint_env=("OLLAMA_BASE_URL",),
        model_env=("OLLAMA_MODEL",),
        capabilities=_COMMON_PROVIDER_CAPABILITIES
        + (_cap("model_generation", "required"), _cap("native_async", "required")),
    ),
)

FRAMEWORKS: tuple[FrameworkDefinition, ...] = (
    FrameworkDefinition(
        name="native",
        capabilities=(_cap("agent_execution", "required"),),
        policy_fields=(
            "max_turns",
            "max_tool_calls",
            "max_tokens",
            "temperature",
            "tool_choice",
            "repair",
            "max_repairs",
            "finalize",
            "trace",
            "strict",
        ),
    ),
    FrameworkDefinition(
        name="langgraph",
        dependency="langgraph",
        extra="langgraph",
        capabilities=(
            _cap("agent_execution", "required"),
            _cap("graph_execution", "required"),
        ),
        policy_fields=(
            "max_turns",
            "max_tool_calls",
            "max_tokens",
            "temperature",
            "tool_choice",
            "repair",
            "max_repairs",
            "finalize",
            "trace",
            "strict",
        ),
    ),
    FrameworkDefinition(
        name="openai-agents",
        dependency="agents",
        extra="openai-agents",
        capabilities=(
            _cap("agent_execution", "required"),
            _cap("handoffs", "optional"),
        ),
        policy_fields=(
            "max_turns",
            "max_tool_calls",
            "max_tokens",
            "temperature",
            "tool_choice",
        ),
    ),
    FrameworkDefinition(
        name="strands",
        dependency="strands",
        extra="strands",
        capabilities=(_cap("agent_execution", "required"), _cap("mcp", "optional")),
        policy_fields=(
            "max_turns",
            "max_tool_calls",
            "max_tokens",
            "temperature",
            "tool_choice",
        ),
    ),
)

PROVIDER_NAMES = tuple(item.name for item in PROVIDERS)
FRAMEWORK_NAMES = tuple(item.name for item in FRAMEWORKS)
MATRIX_CONTRACTS: tuple[MatrixContract, ...] = tuple(
    MatrixContract(provider=provider, framework=framework)
    for provider, framework in product(PROVIDER_NAMES, FRAMEWORK_NAMES)
)


def provider_definition(name: str) -> ProviderDefinition:
    """Return one provider declaration or fail before execution."""

    try:
        return next(item for item in PROVIDERS if item.name == name)
    except StopIteration as exc:
        raise ValueError(
            f"Unknown provider {name!r}; expected one of {PROVIDER_NAMES}."
        ) from exc


def provider_capability(provider: str, capability: str) -> CapabilitySpec:
    """Return one declared provider capability or fail before execution."""

    definition = provider_definition(provider)
    try:
        return next(item for item in definition.capabilities if item.name == capability)
    except StopIteration as exc:
        raise ValueError(
            f"Provider {provider!r} does not declare capability {capability!r}."
        ) from exc


def framework_definition(name: str) -> FrameworkDefinition:
    """Return one framework declaration or fail before execution."""

    try:
        return next(item for item in FRAMEWORKS if item.name == name)
    except StopIteration as exc:
        raise ValueError(
            f"Unknown framework {name!r}; expected one of {FRAMEWORK_NAMES}."
        ) from exc


def framework_policy_fields(name: str) -> tuple[str, ...]:
    """Return policy fields implemented by one framework boundary."""

    return framework_definition(name).policy_fields


def dependency_target(
    name: str,
    *,
    kind: Literal["provider", "framework"],
    package_version: str | None = None,
) -> str | None:
    """Return the canonical package extra target for one optional boundary."""

    definition = (
        provider_definition(name) if kind == "provider" else framework_definition(name)
    )
    if definition.extra is None:
        return None
    resolved_version = package_version
    if resolved_version is None:
        try:
            resolved_version = distribution_version("agentic-systems")
        except PackageNotFoundError:
            resolved_version = None
    suffix = f"=={resolved_version}" if resolved_version else ""
    return f"agentic-systems[{definition.extra}]{suffix}"


def matrix_contract(provider: str, framework: str) -> MatrixContract:
    """Return the declared contract for a provider/framework pair."""

    provider_definition(provider)
    framework_definition(framework)
    return next(
        item
        for item in MATRIX_CONTRACTS
        if item.provider == provider and item.framework == framework
    )


def registry_manifest() -> dict[str, object]:
    """Return the JSON-safe manifest consumed by API, CLI, docs and gates."""

    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "providers": [item.model_dump(mode="json") for item in PROVIDERS],
        "frameworks": [item.model_dump(mode="json") for item in FRAMEWORKS],
        "matrix": [item.model_dump(mode="json") for item in MATRIX_CONTRACTS],
    }


__all__ = [
    "FRAMEWORKS",
    "FRAMEWORK_NAMES",
    "LIVE_ATTESTATION_SCHEMA_VERSION",
    "MATRIX_CONTRACTS",
    "PROVIDERS",
    "PROVIDER_NAMES",
    "REGISTRY_SCHEMA_VERSION",
    "CapabilitySpec",
    "FrameworkDefinition",
    "MatrixContract",
    "ProviderDefinition",
    "dependency_target",
    "framework_definition",
    "framework_policy_fields",
    "matrix_contract",
    "provider_definition",
    "registry_manifest",
    "provider_capability",
]
