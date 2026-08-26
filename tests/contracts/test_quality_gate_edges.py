from __future__ import annotations

import asyncio
from email.message import Message
from datetime import datetime, timezone
from types import SimpleNamespace

from pydantic import ValidationError
import pytest

from agentic_systems import RunPolicy, RunResult
from agentic_systems.core.scheduler import (
    SchedulerConfig,
    _annotate_exception,
    execute_async,
)
from agentic_systems.errors import (
    classify_exception_category,
    exception_status_code,
    execution_error_payload,
)
from agentic_systems.integrations.adapters import openai_agents, strands, tools
from agentic_systems.registry import provider_capability
from agentic_systems.schemas import (
    LIVE_SCENARIO_NAMES,
    LiveAttestation,
    LiveMatrixCase,
    LiveScenarioEvidence,
    validate_live_attestation,
)
from agentic_systems.tools.events import ToolEvent


class _PortableEngine:
    def run(self, *args: object, **kwargs: object) -> RunResult:
        return RunResult(text="sync", engine="python-runtime")

    async def arun(self, *args: object, **kwargs: object) -> RunResult:
        return RunResult(text="async", engine="python-runtime")


class _AttributeLockedError(RuntimeError):
    def __setattr__(self, name: str, value: object) -> None:
        raise RuntimeError("attributes are locked")


def _agent() -> SimpleNamespace:
    return SimpleNamespace(
        engine="python-runtime",
        model="scripted",
        framework_config=SimpleNamespace(agent_kwargs={}, run_kwargs={}),
        available_tools=lambda: [],
    )


def _status_error(**attributes: object) -> RuntimeError:
    error = RuntimeError("provider failed")
    for name, value in attributes.items():
        setattr(error, name, value)
    return error


def test_run_policy_validates_every_optional_limit_boundary() -> None:
    with pytest.raises(ValidationError, match="max_tokens"):
        RunPolicy(max_tokens=0)
    with pytest.raises(ValueError, match="must be >= 1"):
        RunPolicy.validate_optional_positive_ints(0)
    assert RunPolicy.validate_optional_positive_ints(None) is None
    assert RunPolicy.validate_optional_positive_ints(2) == 2


def test_canonical_tool_callable_covers_all_argument_shapes_and_missing_function() -> (
    None
):
    calls: list[object] = []

    def function(value: object = None) -> object:
        return value

    successful = SimpleNamespace(
        name="shape",
        function=function,
        run=lambda payload: (
            calls.append(payload)
            or SimpleNamespace(ok=True, data=payload, errors=[], text="")
        ),
    )
    invoke = tools.canonical_tool_callable(successful)

    assert invoke() is None
    assert invoke(1, 2) == [1, 2]
    assert invoke(value=3) == {"value": 3}
    assert calls == [None, [1, 2], {"value": 3}]

    failed = SimpleNamespace(
        name="failed",
        function=function,
        run=lambda payload: SimpleNamespace(
            ok=False, data=payload, errors=[], text="failed safely"
        ),
    )
    data, ok, error = tools.decode_tool_output(
        tools.canonical_tool_callable(failed)("input")
    )
    assert data == "input"
    assert ok is False
    assert error == {"code": "tool_execution_failed", "message": "failed safely"}

    with pytest.raises(ValueError, match="has no function"):
        tools.canonical_tool_callable(SimpleNamespace(name="empty", function=None))


def test_async_scheduler_returns_non_retryable_values_and_tolerates_locked_errors() -> (
    None
):
    async def failed_value() -> str:
        return "failed"

    value, evidence = asyncio.run(
        execute_async(
            failed_value,
            SchedulerConfig(max_retries=1),
            is_success=lambda _: False,
            should_retry_value=lambda _: False,
        )
    )
    assert value == "failed"
    assert evidence["attempts"] == 1
    _annotate_exception(_AttributeLockedError("locked"), 1, timed_out=False)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_status_error(status_code=418), 418),
        (_status_error(response=SimpleNamespace(status_code=409)), 409),
        (_status_error(response={"StatusCode": 425}), 425),
        (
            _status_error(response={"ResponseMetadata": {"HTTPStatusCode": 503}}),
            503,
        ),
    ],
)
def test_status_extraction_is_sdk_neutral(error: RuntimeError, expected: int) -> None:
    assert exception_status_code(error) == expected


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (TimeoutError("late"), "timeout"),
        (_status_error(status_code=429), "rate_limit"),
        (_status_error(status_code=401), "authentication"),
        (_status_error(status_code=403), "authorization"),
        (_status_error(status_code=500), "transient"),
        (ConnectionError("offline"), "transient"),
        (_status_error(status_code=400), "invalid_request"),
        (RuntimeError("provider"), "provider"),
    ],
)
def test_exception_categories_are_provider_neutral(
    error: BaseException, category: str
) -> None:
    assert classify_exception_category(error) == category


def test_execution_error_includes_status_and_redacts_credentials() -> None:
    error = _status_error(status_code=503)
    error.args = ("api_key=sk-1234567890secret",)
    payload = execution_error_payload(
        error, provider="bedrock-runtime", framework="strands"
    )
    assert payload["details"] == {"status_code": 503}
    assert payload["retryable"] is True
    assert "1234567890secret" not in payload["message"]


@pytest.mark.parametrize(
    "adapter",
    [
        openai_agents.OpenAIAgentsFrameworkAdapter(),
        strands.StrandsFrameworkAdapter(),
    ],
)
def test_deterministic_engines_are_substitutable_across_framework_adapters(
    adapter: object,
) -> None:
    agent = _agent()
    engine = _PortableEngine()
    sync_result = adapter.run(agent, engine, "input", RunPolicy(), mode="eval")
    async_result = asyncio.run(
        adapter.arun(agent, engine, "input", RunPolicy(), mode="eval")
    )
    assert sync_result.meta["framework_adapter"] == adapter.name
    assert async_result.meta["framework_adapter"] == adapter.name


def test_tool_aliases_and_decoding_cover_nested_portable_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tools._portable_tool_name("!!!").startswith("tool_")
    monkeypatch.setattr(tools, "_portable_tool_name", lambda _: "same")
    aliases = tools.ToolNameAliases.from_names(("first", "second"))
    assert aliases.native("first") == "same"
    assert aliases.native("second").startswith("same_")
    assert aliases.map_input([{"tool": "first"}]) == [{"tool": "same"}]
    assert aliases.map_input(({"tool_name": "first"},)) == ({"tool_name": "same"},)
    assert tools.decode_tool_output("not valid [") == ("not valid [", True, None)
    assert tools.decode_tool_output("1") == ("1", True, None)
    assert tools.decode_tool_output("{'answer': 'human'}") == (
        {"answer": "human"},
        True,
        None,
    )


def test_registry_rejects_undeclared_capabilities() -> None:
    with pytest.raises(ValueError, match="does not declare capability"):
        provider_capability("python-runtime", "telepathy")


def test_run_result_retry_projection_covers_each_evidence_channel() -> None:
    assert RunResult._project_public_answer("native") == "native"
    assert RunResult(ok=True).should_retry() is False
    assert RunResult(ok=False, errors=[{"retryable": True}]).should_retry() is True
    event = ToolEvent(
        id="call-1",
        name="lookup",
        ok=False,
        error={"message": "temporary"},
        meta={"retryable": True},
    )
    assert RunResult(ok=False, tool_events=[event]).should_retry() is True
    assert RunResult(ok=False, data={"error": {"category": "timeout"}}).should_retry()
    assert RunResult(ok=False, data={"category": "transient"}).should_retry()


def test_attestation_rejects_duplicate_and_unexpected_scenarios() -> None:
    scenarios = tuple(
        LiveScenarioEvidence(name=name, ok=True) for name in LIVE_SCENARIO_NAMES
    ) + (
        LiveScenarioEvidence(name="inspect", ok=True),
        LiveScenarioEvidence(name="unexpected", ok=True),
    )
    evidence = LiveAttestation(
        created_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
        commit_sha="a" * 40,
        wheel_sha256="b" * 64,
        wheel_filename="agentic_systems-2.1.0-py3-none-any.whl",
        python_version="3.14",
        environment={},
        cases=(
            LiveMatrixCase(
                provider="vllm-runtime",
                framework="native",
                model="qwen",
                ok=True,
                scenarios=scenarios,
            ),
        ),
    )
    with pytest.raises(ValueError) as captured:
        validate_live_attestation(
            evidence,
            expected_commit_sha="a" * 40,
            expected_wheel_sha256="b" * 64,
            expected_pairs={("vllm-runtime", "native")},
            now=datetime(2026, 8, 22, tzinfo=timezone.utc),
        )
    message = str(captured.value)
    assert "duplicate scenarios" in message
    assert "unexpected scenarios" in message


def test_license_evidence_ignores_third_party_notice_bodies() -> None:
    from scripts.check_licenses import _license_evidence

    package = Message()
    package["License"] = (
        "BSD 3-Clause License\n\nThird-party notice: GNU GENERAL PUBLIC LICENSE"
    )

    assert _license_evidence(package) == "BSD 3-Clause License"
