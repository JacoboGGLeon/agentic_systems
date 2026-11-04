"""Contract diagnostics and transport failures remain observable at the boundary."""
from types import SimpleNamespace
import pytest
from pydantic import BaseModel
import agentic_systems as t
from agentic_systems._contracts import _validate_contract, _validate_schema, _policy_model, _invoke_actor_with_connection


def test_schema_type_diagnostic():
    with pytest.raises(TypeError) as caught:
        _validate_schema([])
    assert str(caught.value) == "output_schema must be a JSON Schema dictionary"


@pytest.mark.parametrize("value,message", [
    ({"unknown": 1}, "contract accepts only: completion, expected_output, expected_tool_outputs, failure_policy, input_schema, output_schema, tool_expectation"),
    ({"tool_expectation": {"unknown": 1}}, "tool_expectation accepts only: all_of, allowed, any_of, forbidden, min_count"),
])
def test_unknown_contract_options_keep_namespace(value, message):
    with pytest.raises(ValueError) as caught:
        _validate_contract(value)
    assert str(caught.value) == message


@pytest.mark.parametrize("field", ["any_of", "allowed", "forbidden"])
def test_each_reference_channel_rejects_unavailable_tools(field):
    with pytest.raises(ValueError) as caught:
        _validate_contract({"tool_expectation": {field: ["missing"]}})
    assert str(caught.value) == "Contract references unavailable Tools"


def test_zero_minimum_is_a_valid_contract():
    value = {"tool_expectation": {"min_count": 0}}
    assert _validate_contract(value) == value


def test_custom_policy_model_receives_explicit_python_dump_mode():
    class Policy(BaseModel):
        temperature: float = 0.3
        def model_dump(self, *, mode="python", **kwargs):
            return {"temperature": self.temperature if mode == "python" else 0.9}
    assert _policy_model(Policy()).temperature == 0.3


@pytest.mark.parametrize("provider,text", [("openai-runtime", "[]"), ("python-runtime", "[]")])
def test_native_transport_error_is_reported_only_for_model_provider(monkeypatch, provider, text):
    import agentic_systems._engine.factories as factories
    output = t.RunResult(text=text, data={"final_output": text}, errors=({"code": "previous"},))
    monkeypatch.setattr(factories, "agent", lambda **kwargs: SimpleNamespace(run=lambda value: output))
    result = _invoke_actor_with_connection(SimpleNamespace(name="fixture", instructions="Return JSON", skills=()),
        t.runtime(provider=provider), t.framework("native"), {"output_schema": {"type": "object"}}, {}, {})
    assert result.data == {"final_output": text}
    assert result.text == text
    if provider == "python-runtime":
        assert result.ok is True and result.errors == ({"code": "previous"},)
    else:
        assert result.ok is False
        assert result.errors == ({"code": "previous"}, {"code": "invalid_structured_output", "message": "Structured model output must be a JSON object"})


def test_policy_subclass_json_serializer_is_respected():
    from pydantic import field_serializer
    from agentic_systems._contracts import _Policy, _validate_policy
    class Policy(_Policy):
        @field_serializer("temperature")
        def serialize_temperature(self, value, info):
            return value if info.mode == "json" else 0.9
    assert _validate_policy(Policy(temperature=0.3)) == {"temperature": 0.3}
