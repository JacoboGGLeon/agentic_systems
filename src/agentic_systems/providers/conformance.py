"""Provider-neutral capability profiles and conformance checks."""

from __future__ import annotations

import json
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict

from ..contracts import ValidationResult
from ..engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
    canonical_engine_name,
)
from ..results import RunResult


PROVIDER_CONFORMANCE_SCHEMA_VERSION = "agentic_systems.provider-conformance.v1"
REQUIRED_PROVIDER_CAPABILITIES = (
    "normalized_run_result",
    "stable_engine_identity",
    "structured_tool_evidence",
    "structured_failure",
    "contract_validation",
    "json_serialization",
)
OPTIONAL_PROVIDER_CAPABILITIES = (
    "model_generation",
    "deterministic_execution",
    "native_async",
    "token_usage",
    "streaming",
    "cancellation",
    "offline_execution",
)

CapabilityRequirement = Literal["required", "optional"]
CapabilityStatus = Literal["supported", "degraded", "unsupported"]


class CapabilityDeclaration(BaseModel):
    """One required or optional capability declared by a Provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    requirement: CapabilityRequirement
    status: CapabilityStatus
    detail: str


class ProviderProfile(BaseModel):
    """Static, provider-independent declaration of adapter capabilities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = PROVIDER_CONFORMANCE_SCHEMA_VERSION
    provider: str
    capabilities: tuple[CapabilityDeclaration, ...]

    def capability(self, name: str) -> CapabilityDeclaration:
        for capability in self.capabilities:
            if capability.name == name:
                return capability
        raise KeyError(
            f"Provider {self.provider!r} has no capability declaration for {name!r}. "
            f"Available: {[item.name for item in self.capabilities]}"
        )

    @property
    def required(self) -> tuple[CapabilityDeclaration, ...]:
        return tuple(item for item in self.capabilities if item.requirement == "required")

    @property
    def optional(self) -> tuple[CapabilityDeclaration, ...]:
        return tuple(item for item in self.capabilities if item.requirement == "optional")

    @property
    def degradations(self) -> tuple[CapabilityDeclaration, ...]:
        return tuple(item for item in self.capabilities if item.status == "degraded")

    @property
    def unsupported(self) -> tuple[CapabilityDeclaration, ...]:
        return tuple(item for item in self.capabilities if item.status == "unsupported")

    def check(self, requested: Sequence[str] = (), *, allow_degraded: bool = True) -> ValidationResult:
        """Validate the base contract and any capabilities requested by a caller."""

        result = ValidationResult(ok=True)
        declarations = {item.name: item for item in self.capabilities}
        for name in REQUIRED_PROVIDER_CAPABILITIES:
            declaration = declarations.get(name)
            if declaration is None:
                result.add(
                    "missing_required_capability",
                    f"Provider {self.provider!r} does not declare required capability {name!r}.",
                    path=f"capabilities.{name}",
                )
            elif declaration.requirement != "required" or declaration.status != "supported":
                result.add(
                    "required_capability_not_supported",
                    f"Provider {self.provider!r} must fully support required capability {name!r}.",
                    path=f"capabilities.{name}",
                    meta=declaration.model_dump(mode="json"),
                )

        for name in OPTIONAL_PROVIDER_CAPABILITIES:
            declaration = declarations.get(name)
            if declaration is None:
                result.add(
                    "missing_optional_capability_declaration",
                    f"Provider {self.provider!r} does not declare optional capability {name!r}.",
                    path=f"capabilities.{name}",
                )
            elif declaration.requirement != "optional":
                result.add(
                    "optional_capability_misclassified",
                    f"Provider {self.provider!r} must classify capability {name!r} as optional.",
                    path=f"capabilities.{name}",
                    meta=declaration.model_dump(mode="json"),
                )

        for name in requested:
            declaration = declarations.get(name)
            if declaration is None:
                result.add(
                    "unknown_capability",
                    f"Provider {self.provider!r} has no capability declaration for {name!r}.",
                    path=f"requested.{name}",
                )
            elif declaration.status == "unsupported":
                result.add(
                    "unsupported_capability",
                    f"Provider {self.provider!r} does not support requested capability {name!r}: "
                    f"{declaration.detail}",
                    path=f"requested.{name}",
                    meta=declaration.model_dump(mode="json"),
                )
            elif declaration.status == "degraded":
                result.add(
                    "degraded_capability",
                    f"Provider {self.provider!r} offers degraded capability {name!r}: {declaration.detail}",
                    severity="warning" if allow_degraded else "error",
                    path=f"requested.{name}",
                    meta=declaration.model_dump(mode="json"),
                )
        return result

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ProviderConformanceReport(BaseModel):
    """Serializable result of applying the common Provider contract."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = PROVIDER_CONFORMANCE_SCHEMA_VERSION
    provider: str
    ok: bool
    checks: dict[str, bool]
    issues: list[dict[str, Any]]
    degradations: list[dict[str, Any]]

    def raise_if_failed(self) -> "ProviderConformanceReport":
        if not self.ok:
            raise ValueError(f"Provider conformance failed for {self.provider!r}: {self.issues}")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def provider_profile(provider: str) -> ProviderProfile:
    """Return the normative capability profile for one canonical Provider."""

    canonical = canonical_engine_name(provider)
    return _PROVIDER_PROFILES[canonical]


def provider_profiles() -> tuple[ProviderProfile, ...]:
    """Return all profiles in canonical Provider order."""

    return tuple(_PROVIDER_PROFILES.values())


def evaluate_provider_conformance(
    profile: ProviderProfile | str,
    *,
    success_result: Any,
    failure_result: Any,
    expected_tool_names: Sequence[str] = (),
    expected_mode: str | None = None,
) -> ProviderConformanceReport:
    """Apply one shared observable contract to Provider success and failure results."""

    selected = provider_profile(profile) if isinstance(profile, str) else profile
    checks: dict[str, bool] = {}
    validation = ValidationResult(ok=True)

    def record(name: str, condition: bool, message: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            validation.add(name, message, path=name)

    profile_validation = selected.check()
    record("required_capabilities", profile_validation.ok, "Required Provider capabilities are incomplete.")
    for issue in profile_validation.issues:
        validation.add(
            issue.code,
            issue.message,
            severity=issue.severity,
            path=issue.path,
            meta=issue.meta,
        )

    success_is_result = isinstance(success_result, RunResult)
    failure_is_result = isinstance(failure_result, RunResult)
    record("success_run_result", success_is_result, "Successful execution must return RunResult.")
    record("failure_run_result", failure_is_result, "Failed execution must return RunResult.")

    if success_is_result and failure_is_result:
        record("success_status", success_result.ok is True, "Successful result must set ok=True.")
        record("failure_status", failure_result.ok is False, "Failed result must set ok=False.")
        record(
            "stable_engine_identity",
            success_result.engine == selected.provider and failure_result.engine == selected.provider,
            f"Success and failure must preserve engine identity {selected.provider!r}.",
        )
        record(
            "structured_failure",
            bool(failure_result.errors),
            "Failed Provider execution must retain at least one structured error.",
        )
        record(
            "contract_validation",
            success_result.validation is not None and failure_result.validation is not None,
            "Provider results finalized by Agent must retain contract validation.",
        )
        event_names = {event.name for event in success_result.tool_events if event.ok}
        record(
            "structured_tool_evidence",
            set(expected_tool_names).issubset(event_names),
            f"Successful result is missing required Tool evidence: {sorted(set(expected_tool_names) - event_names)}.",
        )
        record(
            "usage_shape",
            isinstance(success_result.usage, dict) and isinstance(failure_result.usage, dict),
            "Usage must remain a dictionary even when metrics are unavailable.",
        )
        if expected_mode is not None:
            record(
                "mode_preservation",
                success_result.mode == expected_mode and failure_result.mode == expected_mode,
                f"Provider results must preserve requested mode {expected_mode!r}.",
            )
        record(
            "result_invariants",
            success_result.check_invariants().ok and failure_result.check_invariants().ok,
            "Provider results must satisfy RunResult structural invariants.",
        )
        try:
            json.dumps(success_result.to_dict())
            json.dumps(failure_result.to_dict())
            serializable = True
        except (TypeError, ValueError):
            serializable = False
        record("json_serialization", serializable, "Provider results must serialize to JSON.")

    return ProviderConformanceReport(
        provider=selected.provider,
        ok=validation.ok and all(checks.values()),
        checks=checks,
        issues=[issue.model_dump(mode="json") for issue in validation.issues],
        degradations=[item.model_dump(mode="json") for item in selected.degradations],
    )


def _required_capabilities() -> tuple[CapabilityDeclaration, ...]:
    details = {
        "normalized_run_result": "Sync and async Agent execution return the common RunResult envelope.",
        "stable_engine_identity": "Success and failure preserve the canonical Provider identity.",
        "structured_tool_evidence": "Executed Tools remain observable as ordered Tool events.",
        "structured_failure": "Execution failures return structured errors instead of false success.",
        "contract_validation": "Agent finalization applies the same Contract validation semantics.",
        "json_serialization": "Portable result fields support JSON-mode serialization and round-trip.",
    }
    return tuple(
        CapabilityDeclaration(name=name, requirement="required", status="supported", detail=details[name])
        for name in REQUIRED_PROVIDER_CAPABILITIES
    )


def _optional(name: str, status: CapabilityStatus, detail: str) -> CapabilityDeclaration:
    return CapabilityDeclaration(name=name, requirement="optional", status=status, detail=detail)


_REQUIRED = _required_capabilities()
_PROVIDER_PROFILES = {
    PYTHON_RUNTIME_ENGINE: ProviderProfile(
        provider=PYTHON_RUNTIME_ENGINE,
        capabilities=_REQUIRED
        + (
            _optional("model_generation", "unsupported", "python-runtime executes explicit Tool plans; it does not call a model."),
            _optional("deterministic_execution", "supported", "Deterministic Tools and inputs execute without model sampling."),
            _optional("native_async", "degraded", "arun is an async compatibility method over synchronous Tool execution."),
            _optional("token_usage", "degraded", "Usage records request counts, not model token accounting."),
            _optional("streaming", "unsupported", "The Agent Provider contract has no streaming result surface."),
            _optional("cancellation", "unsupported", "Cooperative cancellation is not implemented at the Provider boundary."),
            _optional("offline_execution", "supported", "Execution needs no Provider service when Tools are local."),
        ),
    ),
    OPENAI_RUNTIME_ENGINE: ProviderProfile(
        provider=OPENAI_RUNTIME_ENGINE,
        capabilities=_REQUIRED
        + (
            _optional("model_generation", "supported", "Chat-completions model generation is the native execution path."),
            _optional("deterministic_execution", "unsupported", "Model generation is probabilistic even with constrained settings."),
            _optional("native_async", "supported", "AsyncOpenAI is used by arun."),
            _optional("token_usage", "supported", "Reported Provider token usage is normalized when present."),
            _optional("streaming", "unsupported", "Streaming is not exposed through RunResult execution."),
            _optional("cancellation", "unsupported", "The adapter does not expose cooperative cancellation."),
            _optional("offline_execution", "unsupported", "Execution requires an OpenAI-compatible remote endpoint."),
        ),
    ),
    VLLM_RUNTIME_ENGINE: ProviderProfile(
        provider=VLLM_RUNTIME_ENGINE,
        capabilities=_REQUIRED
        + (
            _optional("model_generation", "supported", "An OpenAI-compatible vLLM endpoint performs generation."),
            _optional("deterministic_execution", "unsupported", "Generated output is not promised to be deterministic."),
            _optional("native_async", "supported", "The async OpenAI-compatible client is used by arun."),
            _optional("token_usage", "degraded", "Usage is normalized only when the configured endpoint reports it."),
            _optional("streaming", "unsupported", "Streaming is not exposed through RunResult execution."),
            _optional("cancellation", "unsupported", "The adapter does not expose cooperative cancellation."),
            _optional("offline_execution", "unsupported", "A running vLLM endpoint is required, even when hosted locally."),
        ),
    ),
    BEDROCK_RUNTIME_ENGINE: ProviderProfile(
        provider=BEDROCK_RUNTIME_ENGINE,
        capabilities=_REQUIRED
        + (
            _optional("model_generation", "supported", "Bedrock Converse is the native generation path."),
            _optional("deterministic_execution", "unsupported", "Managed model output is probabilistic."),
            _optional("native_async", "degraded", "arun delegates synchronous Bedrock execution to a worker thread."),
            _optional("token_usage", "supported", "Bedrock usage records are aggregated into RunResult usage."),
            _optional("streaming", "unsupported", "The Agent engine currently uses non-streaming run_direct."),
            _optional("cancellation", "unsupported", "Worker-thread delegation does not provide cooperative cancellation."),
            _optional("offline_execution", "unsupported", "Execution requires AWS Bedrock Runtime access."),
        ),
    ),
}


__all__ = [
    "PROVIDER_CONFORMANCE_SCHEMA_VERSION",
    "REQUIRED_PROVIDER_CAPABILITIES",
    "OPTIONAL_PROVIDER_CAPABILITIES",
    "CapabilityDeclaration",
    "ProviderProfile",
    "ProviderConformanceReport",
    "provider_profile",
    "provider_profiles",
    "evaluate_provider_conformance",
]
