"""Shared Provider substitution contract and capability-profile tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agentic_systems.contracts import AgentContract, RunPolicy
from agentic_systems.engines.bedrock import BedrockEngine
from agentic_systems.engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
)
from agentic_systems.providers import (
    OPTIONAL_PROVIDER_CAPABILITIES,
    REQUIRED_PROVIDER_CAPABILITIES,
    CapabilityDeclaration,
    OpenAIRuntimeProvider,
    ProviderConformanceReport,
    ProviderProfile,
    PythonRuntimeProvider,
    VLLMRuntimeProvider,
    evaluate_provider_conformance,
    provider_profile,
    provider_profiles,
)
from agentic_systems.providers.base import ToolRegistryRuntime
from agentic_systems.results import RunResult
from agentic_systems.tools import Tool


class FakeResponse:
    def __init__(self, message, *, usage=None):
        self.choices = [SimpleNamespace(message=message)]
        self.usage = usage


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls += 1
        usage = SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        if self.calls == 1:
            call = SimpleNamespace(
                id="call-double",
                function=SimpleNamespace(name="double", arguments='{"value": 21}'),
            )
            message = SimpleNamespace(content="", tool_calls=[call])
        else:
            message = SimpleNamespace(content="42", tool_calls=[])
        return FakeResponse(message, usage=usage)


def _runtime() -> ToolRegistryRuntime:
    runtime = ToolRegistryRuntime(model_id="conformance-model")

    @runtime.tool(name="double", description="Double an integer")
    def double(value: int) -> dict:
        return {"result": value * 2}

    return runtime


def _agent(runtime: ToolRegistryRuntime, *, tools=("double",)):
    return SimpleNamespace(
        name="conformance-agent",
        instructions="Use the declared Tool.",
        tools=tools,
        model="conformance-model",
        contract=AgentContract(),
        framework=None,
        system=SimpleNamespace(_runtime=runtime, model="conformance-model"),
        available_tools=lambda: [Tool(runtime._tools[name].func, name=name) for name in tools],
        info=lambda: {},
    )


def _finalize(result):
    return result.apply_validation(result.validate())


def _python_results():
    runtime = _runtime()
    provider = PythonRuntimeProvider()
    success = provider.run(
        _agent(runtime),
        {"tool": "double", "input": {"value": 21}},
        RunPolicy(),
        mode="conformance",
    )
    failure = provider.run(_agent(runtime, tools=()), {}, RunPolicy(), mode="conformance")
    return provider.profile(), _finalize(success), _finalize(failure)


def _openai_results(provider_class=OpenAIRuntimeProvider):
    runtime = _runtime()
    provider = provider_class(SimpleNamespace(_runtime=runtime), client=FakeClient())
    success = provider.run(_agent(runtime), "Double 21.", RunPolicy(), mode="conformance")
    empty_runtime = ToolRegistryRuntime(model_id="conformance-model")
    failure_provider = provider_class(SimpleNamespace(_runtime=empty_runtime), client=FakeClient())
    failure = failure_provider.run(
        _agent(empty_runtime, tools=()),
        "No tools.",
        RunPolicy(),
        mode="conformance",
    )
    return provider.profile(), _finalize(success), _finalize(failure)


def _vllm_results():
    return _openai_results(VLLMRuntimeProvider)


class FakeBedrockRuntime:
    def __init__(self):
        self.payload = {}

    def run_direct(self, *args, **kwargs):
        return self.payload


def _bedrock_results():
    runtime = _runtime()
    transport = FakeBedrockRuntime()
    engine = BedrockEngine(SimpleNamespace(_runtime=transport, model="conformance-model"))
    agent = _agent(runtime)
    transport.payload = {
        "final_text": "42",
        "messages": [],
        "tool_calls": [
            {
                "tool_use_id": "call-double",
                "tool_name": "double",
                "tool_input": {"value": 21},
                "tool_output": {"data": {"result": 42}},
                "ok": True,
            }
        ],
        "raw_responses": [{"usage": {"inputTokens": 3, "outputTokens": 2, "totalTokens": 5}}],
    }
    success = engine.run(agent, "Double 21.", RunPolicy(), mode="conformance")
    transport.payload = {
        "final_text": "",
        "messages": [],
        "tool_calls": [
            {
                "tool_use_id": "call-failure",
                "tool_name": "double",
                "tool_input": {"value": 21},
                "tool_output": {"data": {"error_type": "RuntimeError", "message": "boom"}},
                "ok": False,
            }
        ],
        "raw_responses": [],
    }
    failure = engine.run(agent, "Fail.", RunPolicy(), mode="conformance")
    return engine.profile(), success, failure


@pytest.mark.parametrize(
    "result_factory",
    [_python_results, _openai_results, _vllm_results, _bedrock_results],
    ids=[PYTHON_RUNTIME_ENGINE, OPENAI_RUNTIME_ENGINE, VLLM_RUNTIME_ENGINE, BEDROCK_RUNTIME_ENGINE],
)
def test_primary_providers_pass_the_same_base_conformance_suite(result_factory) -> None:
    profile, success, failure = result_factory()

    report = evaluate_provider_conformance(
        profile,
        success_result=success,
        failure_result=failure,
        expected_tool_names=["double"],
        expected_mode="conformance",
    )

    assert report.raise_if_failed().ok is True
    assert all(report.checks.values())
    assert json.loads(json.dumps(report.to_dict()))["provider"] == profile.provider


def test_profiles_declare_required_optional_and_adapter_identity() -> None:
    profiles = provider_profiles()
    assert [profile.provider for profile in profiles] == [
        PYTHON_RUNTIME_ENGINE,
        OPENAI_RUNTIME_ENGINE,
        VLLM_RUNTIME_ENGINE,
        BEDROCK_RUNTIME_ENGINE,
    ]
    assert PythonRuntimeProvider.profile() == provider_profile(PYTHON_RUNTIME_ENGINE)
    assert OpenAIRuntimeProvider.profile() == provider_profile(OPENAI_RUNTIME_ENGINE)
    assert VLLMRuntimeProvider.profile() == provider_profile(VLLM_RUNTIME_ENGINE)
    assert BedrockEngine.profile() == provider_profile(BEDROCK_RUNTIME_ENGINE)

    for profile in profiles:
        assert {item.name for item in profile.required} == set(REQUIRED_PROVIDER_CAPABILITIES)
        assert {item.name for item in profile.optional} == set(OPTIONAL_PROVIDER_CAPABILITIES)
        assert all(item.status == "supported" for item in profile.required)
        assert json.loads(json.dumps(profile.to_dict()))["provider"] == profile.provider


def test_degraded_and_unsupported_capabilities_are_explicit() -> None:
    profile = provider_profile(PYTHON_RUNTIME_ENGINE)

    allowed = profile.check(["native_async"])
    assert allowed.ok is True
    assert allowed.issues[0].code == "degraded_capability"
    assert allowed.issues[0].severity == "warning"

    strict = profile.check(["native_async"], allow_degraded=False)
    assert strict.ok is False
    assert strict.issues[0].code == "degraded_capability"

    unsupported = profile.check(["model_generation"])
    assert unsupported.ok is False
    assert unsupported.issues[0].code == "unsupported_capability"

    unknown = profile.check(["telepathy"])
    assert unknown.ok is False
    assert unknown.issues[0].code == "unknown_capability"
    assert profile.capability("token_usage") in profile.degradations
    assert profile.capability("model_generation") in profile.unsupported
    with pytest.raises(KeyError, match="no capability declaration"):
        profile.capability("telepathy")


def test_profile_validation_and_failed_report_messages_are_clear() -> None:
    incomplete = ProviderProfile(
        provider="test-runtime",
        capabilities=(
            CapabilityDeclaration(
                name="normalized_run_result",
                requirement="optional",
                status="degraded",
                detail="Deliberately incomplete test profile.",
            ),
        ),
    )
    validation = incomplete.check()
    assert validation.ok is False
    assert {issue.code for issue in validation.issues} == {
        "missing_required_capability",
        "missing_optional_capability_declaration",
        "required_capability_not_supported",
    }

    misclassified = ProviderProfile(
        provider="test-runtime",
        capabilities=tuple(
            CapabilityDeclaration(name=name, requirement="required", status="supported", detail="base")
            for name in REQUIRED_PROVIDER_CAPABILITIES
        )
        + tuple(
            CapabilityDeclaration(
                name=name,
                requirement="required" if name == "model_generation" else "optional",
                status="supported",
                detail="optional",
            )
            for name in OPTIONAL_PROVIDER_CAPABILITIES
        ),
    )
    assert {issue.code for issue in misclassified.check().issues} == {
        "optional_capability_misclassified"
    }

    report = evaluate_provider_conformance(
        incomplete,
        success_result=object(),
        failure_result=object(),
    )
    assert report.ok is False
    assert report.checks == {
        "required_capabilities": False,
        "success_run_result": False,
        "failure_run_result": False,
    }
    with pytest.raises(ValueError, match="Provider conformance failed"):
        report.raise_if_failed()

    with pytest.raises(ValueError, match="Unknown runtime/provider"):
        provider_profile("unknown-runtime")

    manual = ProviderConformanceReport(
        provider="test-runtime",
        ok=True,
        checks={},
        issues=[],
        degradations=[],
    )
    assert manual.raise_if_failed() is manual



def test_conformance_reports_non_serializable_results(monkeypatch) -> None:
    success = RunResult(
        text="ok",
        ok=True,
        engine=PYTHON_RUNTIME_ENGINE,
        validation={"ok": True, "issues": []},
    )
    failure = RunResult(
        ok=False,
        engine=PYTHON_RUNTIME_ENGINE,
        errors=[{"code": "failed", "message": "expected failure"}],
        validation={"ok": True, "issues": []},
    )
    monkeypatch.setattr(RunResult, "to_dict", lambda self: {"not_json": object()})

    report = evaluate_provider_conformance(
        PYTHON_RUNTIME_ENGINE,
        success_result=success,
        failure_result=failure,
    )

    assert report.ok is False
    assert report.checks["json_serialization"] is False
    assert any(issue["code"] == "json_serialization" for issue in report.issues)
