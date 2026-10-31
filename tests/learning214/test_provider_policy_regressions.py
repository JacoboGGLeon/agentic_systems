"""Canonical provider-boundary regressions; scripted services, no inference."""
from copy import deepcopy
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import agentic_systems as toolkit
from agentic_systems._engine.contracts import AgentContract, RunPolicy
from agentic_systems._engine.providers import openai_runtime as chat

E = Path(__file__).resolve().parents[2] / "revisions/2.1.4/problem-fixes/01"


@pytest.fixture(autouse=True)
def isolated_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(__import__(__name__, fromlist=["E"]), "E", tmp_path)


def save(name, value):
    (E / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
@pytest.mark.parametrize("choice", ["auto", "required", "none"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_capture_bedrock_policy(monkeypatch, framework, choice, asynchronous):
    from botocore.client import BaseClient
    captured = []

    def converse(client, operation, params):
        assert operation == "Converse"
        captured.append(deepcopy(params))
        return {"output": {"message": {"role": "assistant", "content": [{"text": "Offline answer"}]}},
                "stopReason": "end_turn", "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "metrics": {"latencyMs": 1}, "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "offline"}}

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)

    @toolkit.tool
    def echo(value: int) -> dict:
        return {"value": value}

    actor = toolkit.Agent("policy_probe", runtime=toolkit.runtime(provider="bedrock-runtime", model="qwen.qwen3-32b-v1:0",
        region="us-east-2", api_key="offline-test-bearer", max_tokens=128, max_turns=2, max_tool_calls=1),
        framework=toolkit.framework(framework), skills=(toolkit.skill(name="echo", tools=(echo,)),),
        policy={"tool_choice": choice, "repair": False})
    result = asyncio.run(actor.arun({"value": 7})) if asynchronous else actor.run({"value": 7})
    assert len(captured) == 1
    request = captured[0]
    save("policy-" + framework + "-" + choice + "-" + str(asynchronous), {
        "framework": framework, "requested": choice, "async": asynchronous,
        "wire_tool_config": request.get("toolConfig"), "sdk_result_ok": result.ok, "network_requests": 0})
    assert result.check_invariants().ok
    expected = {"auto": {}} if choice == "auto" else {"any": {}}
    assert request.get("toolConfig") is None if choice == "none" else request["toolConfig"]["toolChoice"] == expected


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("variant", ["text", "empty", "repeated_native_call", "repeated_textual_call"])
def test_replay_native_ollama_completion(variant, asynchronous):
    calls = []
    effects = []
    name = "mark_native"
    tools = [{"type": "function", "function": {"name": name, "parameters": {"type": "object",
        "properties": {"value": {"type": "integer"}, "trail": {"type": "array", "items": {"type": "string"}}},
        "required": ["value", "trail"]}}}]

    def call(value=42, trail=None):
        return SimpleNamespace(id="call-" + str(len(calls)), function=SimpleNamespace(name=name,
            arguments=json.dumps({"value": value, "trail": [] if trail is None else trail})))

    def response(**kwargs):
        calls.append({"tools": deepcopy(kwargs.get("tools")), "tool_choice": kwargs.get("tool_choice")})
        if len(calls) == 1:
            message = SimpleNamespace(content="", tool_calls=[call()])
        elif variant == "repeated_native_call":
            message = SimpleNamespace(content="", tool_calls=[call(43, ["native"])])
        elif variant == "repeated_textual_call":
            message = SimpleNamespace(content='mark_native({"value":43,"trail":["native"]})', tool_calls=[])
        else:
            message = SimpleNamespace(content="done" if variant == "text" else "", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15))

    async def async_response(**kwargs):
        return response(**kwargs)

    def execute(name, arguments):
        effects.append(arguments)
        return {"value": arguments["value"] + 1, "trail": [*arguments["trail"], "native"]}

    runtime = SimpleNamespace(tools=[SimpleNamespace(name=name)], execute_tool=execute)
    actor = SimpleNamespace(name="probe", model="offline-model", available_tools=lambda: runtime.tools,
        framework_config=SimpleNamespace(name="native"),
        contract=AgentContract(must_call=[name], completion="when_required_tools_satisfied"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=async_response if asynchronous else response)))
    kwargs = dict(runtime=runtime, agent=actor, policy=RunPolicy(max_tool_calls=1, max_turns=3, max_tokens=128, repair=False),
                  mode="default", runtime_engine="ollama-runtime")
    messages = [{"role": "user", "content": "Increment 42 and append native once"}]
    result = asyncio.run(chat._run_chat_loop_async(client, messages, tools, **kwargs)) if asynchronous else chat._run_chat_loop(client, messages, tools, **kwargs)
    assert len(calls) == 2 and len(effects) == 1
    assert calls[1]["tools"] is None
    assert result.ok is (variant == "text")
    if variant.startswith("repeated"):
        assert result.meta["rejected_tool_calls"]
        assert result.errors[0]["code"] == "rejected_tool_calls"
    save("ollama-" + variant + "-" + str(asynchronous), {"variant": variant, "async": asynchronous,
        "calls": calls, "effects": effects, "result": result.to_dict(), "network_requests": 0,
        "second_provider_reply_was_empty": variant == "empty"})


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
@pytest.mark.parametrize("scenario", ["correct", "wrong_answer", "missing_tool", "empty_answer"])
def test_studio_with_real_sdk_and_scripted_service(monkeypatch, framework, scenario):
    from botocore.client import BaseClient
    from agentic_systems_studio import ConversationConfig, build_conversational_system
    from agentic_systems_studio import budget
    monkeypatch.setattr(budget, "ensure_budget", lambda: None)
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "offline-test-bearer")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "qwen.qwen3-32b-v1:0")
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setenv("BEDROCK_BASE_URL", "https://bedrock-runtime.us-east-2.amazonaws.com")
    calls = []

    def converse(client, operation, params):
        assert operation == "Converse"
        names = [entry.get("toolSpec", {}).get("name") for entry in params.get("toolConfig", {}).get("tools", [])]
        system_text = "\n".join(block.get("text", "") for block in params.get("system", []))
        calculator = names == ["safe_calculate"] or "Call safe_calculate once" in system_text
        calls.append({"stage": "calculator" if calculator else "assistant", "tool_config": deepcopy(params.get("toolConfig"))})
        has_result = any("toolResult" in block for message in params["messages"] for block in message["content"])
        if calculator and not has_result and scenario != "missing_tool":
            content = [{"toolUse": {"toolUseId": "offline-calculation", "name": "safe_calculate", "input": {"expression": "7*6"}}}]
            stop = "tool_use"
        else:
            answer = "42" if calculator else "El resultado es 999." if scenario == "wrong_answer" else "" if scenario == "empty_answer" else "El resultado es 42."
            content, stop = [{"text": answer}], "end_turn"
        return {"output": {"message": {"role": "assistant", "content": content}}, "stopReason": stop,
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 1},
            "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "offline-studio"}}

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)
    studio = build_conversational_system(ConversationConfig(provider="bedrock-runtime", framework=framework,
        model="qwen.qwen3-32b-v1:0", max_response_repairs=0, timeout_s=10))
    result = studio.run("Calcula 7 * 6.", history=[{"role": "user", "content": "Mi referencia es LIMA"}])
    events = [event for node in result.walk() for event in node.tool_events if event.name == "safe_calculate"]
    save("studio-" + framework + "-" + scenario, {"framework": framework, "scenario": scenario,
        "calls": calls, "calculation_events": [{"ok": event.ok, "output": event.output} for event in events],
        "result": result.to_dict(), "network_requests": 0})
    if scenario == "missing_tool":
        assert not result.ok and not any(call["stage"] == "assistant" for call in calls)
    elif scenario in {"empty_answer", "wrong_answer"}:
        assert not result.ok
    else:
        assert result.ok and events
        assert result.data["answer"] == ("El resultado es 999." if scenario == "wrong_answer" else "El resultado es 42.")


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_none_must_prevent_unexpected_tool_effect(monkeypatch, framework, asynchronous):
    """A nonconforming provider must not override a caller's no-Tools policy."""
    from botocore.client import BaseClient
    effects = []
    calls = []

    def converse(client, operation, params):
        calls.append(deepcopy(params.get("toolConfig")))
        has_result = any("toolResult" in block for message in params["messages"] for block in message["content"])
        content = [{"text": "done"}] if has_result else [{"toolUse": {"toolUseId": "unexpected-call", "name": "record_value", "input": {"value": 7}}}]
        return {"output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "end_turn" if has_result else "tool_use", "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "metrics": {"latencyMs": 1}, "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "offline-none"}}

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)

    @toolkit.tool
    def record_value(value: int) -> dict:
        effects.append(value)  # A local list only; no real external effect.
        return {"value": value}

    actor = toolkit.Agent("no_tools", runtime=toolkit.runtime(provider="bedrock-runtime", model="qwen.qwen3-32b-v1:0",
        region="us-east-2", api_key="offline-test-bearer", max_tokens=128, max_turns=2, max_tool_calls=1),
        framework=toolkit.framework(framework), skills=(toolkit.skill(name="record", tools=(record_value,)),),
        policy={"tool_choice": "none", "repair": False})
    result = asyncio.run(actor.arun({"value": 7})) if asynchronous else actor.run({"value": 7})
    save("none-effect-" + framework + "-" + str(asynchronous), {"framework": framework, "async": asynchronous,
        "effects": effects, "requests": calls, "result": result.to_dict(), "network_requests": 0,
        "service_reply": "adversarial simulated ToolUse despite none; no real provider was called"})
    assert effects == [], "The no-Tools policy must reject an unexpected call before executing it"


def test_capture_native_bedrock_synthesis_failure(monkeypatch):
    from botocore.client import BaseClient
    calls, effects = [], []

    def converse(client, operation, params):
        calls.append(deepcopy(params))
        if len(calls) == 2:
            raise RuntimeError("OFFLINE_SYNTHESIS_FAILURE_SENTINEL")
        content = [{"toolUse": {"toolUseId": "once", "name": "echo_value", "input": {"value": 7}}}] if len(calls) == 1 else [{"text": "Recovered on a later request"}]
        return {"output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "tool_use" if len(calls) == 1 else "end_turn",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 1},
            "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "offline-synthesis"}}

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)

    @toolkit.tool
    def echo_value(value: int) -> dict:
        effects.append(value)
        return {"value": value}

    actor = toolkit.Agent("synthesis_probe", runtime=toolkit.runtime(provider="bedrock-runtime", model="qwen.qwen3-32b-v1:0",
        region="us-east-2", api_key="offline-test-bearer", max_tokens=128, max_turns=2, max_tool_calls=1, max_retries=0),
        skills=(toolkit.skill(name="echo", tools=(echo_value,)),),
        contract={"tool_expectation": {"all_of": ["echo_value"]}, "completion": "when_required_tools_satisfied"},
        policy={"repair": False})
    result = actor.run({"value": 7})
    payload = result.to_dict()
    save("bedrock-synthesis-failure", {"actual_simulated_dispatches": len(calls), "effects": effects,
        "failure_sentinel_in_result": "OFFLINE_SYNTHESIS_FAILURE_SENTINEL" in json.dumps(payload),
        "result": payload, "network_requests": 0})
    assert effects == [7]
    assert len(calls) == 2
    assert not result.ok
    assert "OFFLINE_SYNTHESIS_FAILURE_SENTINEL" in json.dumps(payload)
    assert result.usage["requests"] == 2


@pytest.mark.parametrize("value, expected", [("", ""), ("  ", "  "), (None, ""), (0, "0"), (False, "false"), ({"amount": None}, '{"amount": null}')])
def test_public_output_preserves_empty_and_valid_values(value, expected):
    from agentic_systems._engine.integrations.adapters.openai_agents import _output_text
    assert _output_text(value) == expected


def test_strands_policy_resets_on_reused_model():
    from agentic_systems._engine.integrations.adapters.strands import _configure_model
    model = SimpleNamespace(config={}, update_config=lambda **kwargs: None)
    for choice in ("required", "none", "auto"):
        _configure_model(model, RunPolicy(tool_choice=choice, max_tool_calls=1), "default")
        assert model._agentic_systems_tool_choice == choice
        assert model._agentic_systems_emitted_tool_calls == 0


@pytest.mark.parametrize("answer, accepted", [("42", True), ("7 * 6 = 42", True), ("999", False), ("42 y 999", False), ("No sé", False)])
def test_studio_numeric_evidence(answer, accepted):
    from agentic_systems_studio.conversation import _validate_calculation_answer
    evidence = [{"result": 42, "expression": "7*6"}]
    if accepted:
        _validate_calculation_answer(answer, evidence)
    else:
        with pytest.raises(ValueError):
            _validate_calculation_answer(answer, evidence)
