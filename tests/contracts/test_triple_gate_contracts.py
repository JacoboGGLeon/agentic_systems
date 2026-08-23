from __future__ import annotations

import json

from hypothesis import given, strategies as st
from pydantic import TypeAdapter, ValidationError
import pytest

import agentic_systems as toolkit
from agentic_systems.normalization import (
    contains_leading_reasoning,
    project_public_text,
)
from agentic_systems.protocols import AsyncRunner, FrameworkAdapter, SyncRunner
from agentic_systems.registry import (
    FRAMEWORK_NAMES,
    MATRIX_CONTRACTS,
    PROVIDER_NAMES,
    dependency_target,
    framework_definition,
    matrix_contract,
    provider_definition,
    registry_manifest,
)
from agentic_systems.schemas import (
    AgentSpec,
    BedrockRuntimeSpec,
    EnvironmentSpec,
    EvalSpec,
    ExecutionError,
    ExecutionLimits,
    FrameworkSpec,
    NormalizedModelOutput,
    OllamaRuntimeSpec,
    OpenAIRuntimeSpec,
    ProviderRuntimeSpec,
    PythonRuntimeSpec,
    RuntimeConfigSchema,
    RuntimeIdentity,
    SkillSpec,
    SystemSpec,
    ToolSpec,
    UsageInfo,
    VLLMRuntimeSpec,
)


def test_dependency_targets_come_from_the_canonical_registry() -> None:
    assert (
        dependency_target("openai-agents", kind="framework", package_version="2.1.0")
        == "agentic-systems[openai-agents]==2.1.0"
    )
    assert (
        dependency_target("vllm-runtime", kind="provider", package_version="2.1.0")
        == "agentic-systems[vllm-client]==2.1.0"
    )
    assert (
        dependency_target("native", kind="framework", package_version="2.1.0") is None
    )


@given(
    max_turns=st.integers(min_value=1, max_value=1000),
    max_tool_calls=st.one_of(st.none(), st.integers(min_value=0, max_value=1000)),
    max_tokens=st.one_of(st.none(), st.integers(min_value=1, max_value=100_000)),
    retries=st.integers(min_value=0, max_value=20),
)
def test_execution_limits_json_round_trip(
    max_turns: int,
    max_tool_calls: int | None,
    max_tokens: int | None,
    retries: int,
) -> None:
    limits = ExecutionLimits(
        max_turns=max_turns,
        max_tool_calls=max_tool_calls,
        max_tokens=max_tokens,
        max_retries=retries,
    )
    restored = ExecutionLimits.model_validate_json(limits.model_dump_json())
    assert restored == limits


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_turns", 0),
        ("max_turns", -1),
        ("max_tool_calls", -1),
        ("max_tokens", 0),
        ("max_retries", -1),
        ("max_repairs", -1),
        ("max_concurrency", 0),
        ("timeout_s", 0),
        ("backoff_s", -1),
    ],
)
def test_execution_limits_reject_invalid_boundaries(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        ExecutionLimits.model_validate({field: value})


def test_execution_limits_are_strict_and_scheduler_delegates() -> None:
    with pytest.raises(ValidationError):
        ExecutionLimits(max_tool_calls="0")  # type: ignore[arg-type]
    scheduler = toolkit.scheduler(max_tool_calls=0, max_turns=1, timeout_s=1)
    assert scheduler.execution_limits().max_tool_calls == 0
    assert toolkit.RunPolicy(max_tool_calls=0).max_tool_calls == 0
    assert scheduler.policy_overrides() == {"max_turns": 1, "max_tool_calls": 0}


def test_zero_tool_limit_is_enforced_by_python_runtime() -> None:
    @toolkit.tool
    def increment(value: int) -> dict[str, int]:
        return {"value": value + 1}

    runtime = toolkit.runtime(
        provider="python-runtime", scheduler=toolkit.scheduler(max_tool_calls=0)
    )
    agent = toolkit.agent(name="no-tools", tools=[increment], runtime=runtime)
    result = agent.run({"tool": "increment", "input": {"value": 1}})
    assert result.ok is False
    assert result.data["error"]["code"] == "max_tool_calls_exceeded"
    assert result.meta["scheduler"]["max_tool_calls"] == 0


@pytest.mark.parametrize(
    "runtime",
    [
        PythonRuntimeSpec(),
        OpenAIRuntimeSpec(api_key="secret-openai"),
        OllamaRuntimeSpec(endpoint="http://localhost:11434/v1"),
        BedrockRuntimeSpec(api_key="secret-bedrock", region_name="us-east-2"),
        VLLMRuntimeSpec(api_key="secret-vllm", endpoint="http://localhost:8000/v1"),
    ],
)
def test_runtime_discriminator_round_trip_and_secret_redaction(runtime: object) -> None:
    adapter = TypeAdapter(ProviderRuntimeSpec)
    dumped = runtime.model_dump(mode="json")  # type: ignore[union-attr]
    encoded = json.dumps(dumped)
    assert "secret-" not in encoded
    restored = adapter.validate_python(dumped)
    assert restored.provider == runtime.provider  # type: ignore[union-attr]
    assert "secret-" not in repr(runtime)


def test_runtime_discriminator_rejects_unknown_provider_and_extra_fields() -> None:
    adapter = TypeAdapter(ProviderRuntimeSpec)
    with pytest.raises(ValidationError):
        adapter.validate_python({"provider": "unknown"})
    with pytest.raises(ValidationError):
        PythonRuntimeSpec(unknown=True)  # type: ignore[call-arg]


def test_all_persisted_specs_have_stable_schema_and_round_trip() -> None:
    specs = [
        FrameworkSpec(name="native"),
        ToolSpec(name="math.add", input_schema={"type": "object"}),
        SkillSpec(name="math", tool_names=("math.add",)),
        AgentSpec(name="calculator", tool_names=("math.add",)),
        SystemSpec(name="workflow", component_names=("calculator",)),
        EnvironmentSpec(name="episodes", system_name="workflow", max_episodes=2),
        EvalSpec(name="quality", target_name="workflow", target_kind="system"),
    ]
    for spec in specs:
        schema_a = json.dumps(type(spec).model_json_schema(), sort_keys=True)
        schema_b = json.dumps(type(spec).model_json_schema(), sort_keys=True)
        assert schema_a == schema_b
        restored = type(spec).model_validate_json(spec.model_dump_json())
        assert restored == spec
        assert spec.schema_version == "agentic_systems.spec.v1"


def test_typed_result_projections_are_closed_and_serializable() -> None:
    error = ExecutionError(
        category="timeout",
        message="deadline",
        provider="openai-runtime",
        framework="native",
        code="timeout",
        retryable=True,
        cause_type="TimeoutError",
    )
    output = NormalizedModelOutput(
        answer_text="done",
        structured_output={"value": 42},
        usage=UsageInfo(input_tokens=3, output_tokens=2, total_tokens=5, requests=1),
        errors=(error,),
        raw_evidence=({"id": "sanitized"},),
    )
    identity = RuntimeIdentity(
        provider="openai-runtime", framework="native", model="test"
    )
    assert json.loads(output.model_dump_json())["structured_output"] == {"value": 42}
    assert identity.model_dump()["provider"] == "openai-runtime"
    assert (
        RuntimeConfigSchema(
            limits=ExecutionLimits(max_tool_calls=0)
        ).limits.max_tool_calls
        == 0
    )
    with pytest.raises(ValidationError):
        UsageInfo(total_tokens=-1)


def test_registry_is_the_complete_canonical_5_by_4_manifest() -> None:
    assert len(PROVIDER_NAMES) == 5
    assert len(FRAMEWORK_NAMES) == 4
    assert len(MATRIX_CONTRACTS) == 20
    assert {(item.provider, item.framework) for item in MATRIX_CONTRACTS} == set(
        __import__("itertools").product(PROVIDER_NAMES, FRAMEWORK_NAMES)
    )
    manifest = registry_manifest()
    assert manifest["schema_version"] == "agentic_systems.registry.v1"
    assert len(manifest["matrix"]) == 20
    for provider in PROVIDER_NAMES:
        assert provider_definition(provider).name == provider
    for framework in FRAMEWORK_NAMES:
        assert framework_definition(framework).name == framework
    assert matrix_contract("python-runtime", "native").status == "supported"
    with pytest.raises(ValueError, match="Unknown provider"):
        provider_definition("invalid")
    with pytest.raises(ValueError, match="Unknown framework"):
        framework_definition("invalid")


@pytest.mark.parametrize("tag", ["thinking", "think", "reasoning"])
def test_reasoning_projection_removes_one_balanced_leading_block(tag: str) -> None:
    projected = project_public_text(f"  <{tag}>private</{tag}>\nPublic answer")
    assert projected.text == "Public answer"
    assert projected.reasoning_present is True
    assert projected.reasoning_format == f"<{tag}>"
    assert projected.removed is True


def test_reasoning_projection_preserves_legitimate_or_uncertain_tags() -> None:
    samples = (
        "Use <thinking> as an XML example.",
        "```xml\n<thinking>example</thinking>\n```",
        "<thinking>unbalanced private text",
    )
    assert project_public_text(samples[0]).text == samples[0]
    assert project_public_text(samples[1]).text == samples[1]
    uncertain = project_public_text(samples[2])
    assert uncertain.text == samples[2]
    assert uncertain.reasoning_present is True
    assert uncertain.removed is False
    assert contains_leading_reasoning(samples[2]) is True
    assert contains_leading_reasoning(samples[0]) is False


def test_run_result_public_projection_hides_reasoning_and_keeps_raw_evidence() -> None:
    raw = {"content": "<thinking>private chain</thinking>Visible"}
    result = toolkit.RunResult(
        text="<thinking>private chain</thinking>Visible",
        final={"text": "<thinking>private chain</thinking>Visible"},
        raw_responses=[raw],
        engine="bedrock-runtime",
        model="nova",
    )
    assert result.text == "Visible"
    assert result.final["text"] == "Visible"
    assert result.raw_responses == [raw]
    assert result.meta["reasoning"] == {
        "present": True,
        "format": "<thinking>",
        "removed_from_public_text": True,
    }
    assert result.check_invariants().ok is True

    result.text = "<think>mutated</think>unsafe"
    codes = {issue.code for issue in result.check_invariants().issues}
    assert "reasoning_exposed_in_public_answer" in codes


def test_small_protocols_support_structural_substitution() -> None:
    class Runner:
        def run(self, input: object, **kwargs: object) -> toolkit.RunResult:
            return toolkit.RunResult(text=str(input), engine="python-runtime")

        async def arun(self, input: object, **kwargs: object) -> toolkit.RunResult:
            return self.run(input, **kwargs)

    class Adapter(Runner):
        name = "test"

        def prepare(self, agent: object, engine: object) -> tuple[object, object]:
            return agent, engine

        def run(
            self, agent: object, engine: object, input: object, **kwargs: object
        ) -> toolkit.RunResult:
            return toolkit.RunResult(text=str(input), engine="python-runtime")

        async def arun(
            self, agent: object, engine: object, input: object, **kwargs: object
        ) -> toolkit.RunResult:
            return self.run(agent, engine, input, **kwargs)

    assert isinstance(Runner(), SyncRunner)
    assert isinstance(Runner(), AsyncRunner)
    assert isinstance(Adapter(), FrameworkAdapter)


def test_dependency_target_resolves_installed_version_or_source_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agentic_systems.registry as registry

    monkeypatch.setattr(registry, "distribution_version", lambda name: "2.1.0")
    assert (
        registry.dependency_target("openai-agents", kind="framework")
        == "agentic-systems[openai-agents]==2.1.0"
    )

    def missing(name: str) -> str:
        raise registry.PackageNotFoundError(name)

    monkeypatch.setattr(registry, "distribution_version", missing)
    assert (
        registry.dependency_target("openai-agents", kind="framework")
        == "agentic-systems[openai-agents]"
    )
