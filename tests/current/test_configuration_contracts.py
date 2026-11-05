"""Configuration inspection and adapter translation retain caller decisions."""
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, field_serializer

import agentic_systems as t
from agentic_systems._contracts import _validate_contract, _validate_schema, _policy_model, _closed, _invoke_actor_with_connection


def test_runtime_inspection_retains_nondefault_controls_without_secrets():
    config = t.runtime(provider="openai-runtime", model="fixture", endpoint="https://example.invalid",
                       api_key="secret", timeout_s=13, max_retries=2, max_tool_calls=3,
                       max_turns=4, max_tokens=17, backoff_s=0.25, max_concurrency=2)
    assert config.inspect() == {
        "provider": "openai-runtime", "model": "fixture", "region": None, "endpoint": "https://example.invalid",
        "api_key_configured": True, "session_configured": False, "authentication_mode": "provider-configuration",
        "timeout_s": 13, "max_retries": 2, "max_tool_calls": 3, "max_turns": 4, "max_tokens": 17,
        "backoff_s": 0.25, "max_concurrency": 2}


@pytest.mark.parametrize("flag", ["--host", "--port", "--served-model-name", "--gpu-memory-utilization",
    "--max-model-len", "--max-num-seqs", "--tool-call-parser", "--reasoning-parser",
    "--enable-auto-tool-choice", "--api-key", "--generation-config"])
def test_every_owned_server_flag_is_rejected_before_process_creation(flag):
    with pytest.raises(ValueError, match="extra_args cannot override managed server parameters"):
        t.model_server(t.model_artifact("weights"), extra_args=(flag + "=override",))


def test_server_default_command_and_health_keep_connection_identity(monkeypatch):
    import agentic_systems._engine.serving.vllm as impl
    server = t.model_server(t.model_artifact("weights"))
    spec = server._resource.spec
    assert spec.startup_timeout_s == 600.0
    assert spec.log_path == "vllm-server.log"
    assert spec.tool_call_parser == "hermes" and spec.enable_auto_tool_choice is True
    assert spec.api_key.get_secret_value() == "vllm"
    monkeypatch.setattr(impl.shutil, "which", lambda binary: binary)
    assert server.command[0] == "vllm"
    assert "--tool-call-parser" in server.command
    assert server.inspect()["command"] == list(server.command)
    endpoint = server.endpoint
    assert endpoint.url == "http://127.0.0.1:8000/v1"
    assert endpoint.backend == "vllm" and endpoint.model == "weights"
    assert endpoint.api_key_configured is True
    private = t.model_server(t.model_artifact("weights"), api_key="private-token")
    monkeypatch.setattr(type(private._resource), "health", lambda self: SimpleNamespace(
        status="unhealthy", endpoint=self.endpoint, detail="private-token refused"))
    assert private.health().detail == "[REDACTED] refused"


@pytest.mark.parametrize("field", ["agent_kwargs", "run_kwargs"])
def test_reserved_framework_options_cannot_override_toolkit_on_either_side(field):
    with pytest.raises(ValueError, match="Framework options cannot override toolkit-owned configuration"):
        t.framework("openai-agents", **{field: {"max_tokens": 3}})
    with pytest.raises(ValueError, match="Nested SDK options cannot override toolkit-owned configuration"):
        t.framework("openai-agents", **{field: {"model_settings": {"max_tokens": 3}}})
    assert t.framework("openai-agents", **{field: {"model_settings": {"max_tokens": None}}})


@pytest.mark.parametrize("key", ["all_of", "any_of", "allowed", "forbidden"])
def test_each_expectation_requires_a_list_of_names(key):
    with pytest.raises(TypeError, match=key + " requires a list of Tool names"):
        _validate_contract({"tool_expectation": {key: "charge"}}, tools=("charge",))


def test_budget_boundary_input_schema_and_expected_tool_output_validation():
    contract = {"tool_expectation": {"min_count": 2}}
    assert _validate_contract(contract) == contract
    assert _validate_contract(contract, runtime=SimpleNamespace(max_tool_calls=2)) == contract
    with pytest.raises(TypeError, match="expected_tool_outputs must be a dictionary"):
        _validate_contract({"expected_tool_outputs": []})
    with pytest.raises(TypeError, match="output_schema must be a JSON Schema dictionary"):
        _validate_contract({"input_schema": []})
    local = {"$defs": {"item": {"type": "integer"}}, "properties": {"value": {"$ref": "#/$defs/item"}}}
    assert _validate_schema(local) == local
    with pytest.raises(ValueError, match="^Schema references must be local; no remote resolution$"):
        _validate_schema({"allOf": [{"properties": {"value": {"$ref": "https://example.invalid"}}}]})
    with pytest.raises(ValueError, match="^options accepts only: a, b$"):
        _closed({"unknown": True}, {"a", "b"}, "options")


def test_pydantic_policy_input_preserves_nondefault_settings():
    class Policy(BaseModel):
        temperature: float = 0.75
        repair: bool = True
    value = _policy_model(Policy())
    assert value.temperature == 0.75 and value.repair is True


def test_policy_model_uses_python_serialization_contract():
    class Policy(BaseModel):
        temperature: float = 0.75

        @field_serializer("temperature")
        def serialize_temperature(self, value, info):
            return value if info.mode == "python" else "invalid"

    assert _policy_model(Policy()).temperature == 0.75


@pytest.mark.parametrize("failure_policy", ["allow", "no_unresolved"])
@pytest.mark.parametrize("expectation", [{"all_of": ["charge"], "forbidden": ["refund"]}, {"any_of": ["charge"]}])
def test_actor_bridge_translates_contract_and_policy_without_schema_leakage(monkeypatch, failure_policy, expectation):
    import agentic_systems._engine.factories as factories
    observed = {}
    class Actor:
        def run(self, value):
            observed["input"] = value
            return t.RunResult(data={"receipt": 4}, engine="openai-runtime")
    def factory(**kwargs):
        observed.update(kwargs)
        return Actor()
    monkeypatch.setattr(factories, "agent", factory)
    config = t.runtime(provider="openai-runtime", model="fixture", max_tokens=11, max_turns=2, max_tool_calls=3)
    owner = SimpleNamespace(name="payments", skills=(), instructions="Use policy.")
    contract = {"input_schema": {"type": "object"}, "output_schema": {"type": "object"},
                "tool_expectation": expectation, "failure_policy": failure_policy}
    output = _invoke_actor_with_connection(owner, config, t.framework("native"), contract, {"temperature": 0.3}, {"amount": 4})
    assert output.data == {"receipt": 4}
    assert observed["input"] == {"amount": 4} and observed["name"] == "payments"
    assert observed["skills"] == []
    assert observed["contract"] == {
        "tool_expectation": {k: v for k, v in expectation.items() if k != "forbidden"},
        "failure_policy": failure_policy, "must_call": expectation.get("all_of", []),
        "must_not_call": expectation.get("forbidden", []),
        "require_no_unresolved_tool_failures": failure_policy != "allow"}
    assert observed["policy"] == {"temperature": 0.3, "max_tokens": 11, "max_turns": 2, "max_tool_calls": 3}
    assert observed["instructions"] == 'Use policy.\nReturn a JSON object satisfying this JSON Schema: {"type": "object"}'


@pytest.mark.parametrize("count", [-1, True, 1.5, "1"])
def test_invalid_minimum_tool_count_retains_actionable_diagnostic(count):
    with pytest.raises(ValueError, match="^min_count must be nonnegative$"):
        _validate_contract({"tool_expectation": {"min_count": count}}, ())
