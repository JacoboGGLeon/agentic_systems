import os
from dataclasses import dataclass

from pydantic import BaseModel

from agentic_systems.providers.bedrock_runtime import BedrockRuntime, ToolEnvelope


def build_runtime() -> BedrockRuntime:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return BedrockRuntime(model_id="qwen.qwen3-32b-v1:0", region_name="us-east-1")


class Profile(BaseModel):
    user_id: str
    tier: str


@dataclass
class Metric:
    name: str
    value: float


def test_tool_envelope_data_is_always_dict_for_supported_outputs():
    runtime = build_runtime()

    samples = [
        ({"result": 42}, "object"),
        (["a", "b"], "list"),
        ("hola", "text"),
        (42, "number"),
        (True, "boolean"),
        (None, "null"),
        (Profile(user_id="jacobo", tier="gold"), "pydantic"),
        (Metric(name="coverage", value=1.0), "dataclass"),
    ]

    for value, expected_kind in samples:
        envelope = runtime.to_envelope(value, tool_name="sample")
        assert isinstance(envelope, ToolEnvelope)
        assert envelope.kind == expected_kind
        assert isinstance(envelope.data, dict)
        assert envelope.meta["serializer"] == "BedrockRuntime.ToolEnvelope.v1"


def test_registered_tools_return_canonical_dict_payloads():
    runtime = build_runtime()

    @runtime.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos numeros."""
        return {"operation": "sumar", "result": a + b}

    @runtime.tool
    def keywords(text: str) -> list[str]:
        """Extrae keywords simples."""
        return [token.lower() for token in text.split()[:2]]

    sum_env = runtime.execute_tool("sumar", {"a": 17, "b": 25})
    kw_env = runtime.execute_tool("keywords", {"text": "Bedrock agents"})

    assert sum_env.ok is True
    assert sum_env.data == {"operation": "sumar", "result": 42}
    assert isinstance(sum_env.data, dict)

    assert kw_env.ok is True
    assert kw_env.kind == "list"
    assert kw_env.data == {"items": ["bedrock", "agents"]}
    assert isinstance(kw_env.data, dict)


def test_validation_errors_are_dict_payloads():
    runtime = build_runtime()

    @runtime.tool
    def dividir(a: float, b: float) -> dict:
        """Divide dos numeros."""
        if b == 0:
            raise ZeroDivisionError("division by zero")
        return {"operation": "dividir", "result": a / b}

    envelope = runtime.execute_tool("dividir", {"a": 1, "b": 0})
    assert envelope.ok is False
    assert isinstance(envelope.data, dict)
    assert envelope.data["error_type"] == "ZeroDivisionError"


def test_unknown_tool_is_canonical_error_envelope():
    runtime = build_runtime()
    envelope = runtime.execute_tool("missing_tool", {})
    assert envelope.ok is False
    assert isinstance(envelope.data, dict)
    assert envelope.data["error_type"] == "UnknownToolError"


def test_parse_tool_output_repairs_runtime_non_dict_data():
    raw = {
        "kind": "list",
        "tool_name": "runtime_keywords",
        "ok": True,
        "data": ["a", "b"],
        "meta": {},
    }
    parsed = BedrockRuntime.parse_tool_output(raw)
    assert isinstance(parsed["data"], dict)
    assert parsed["data"] == {"items": ["a", "b"]}


def test_parse_framework_tool_output_rejects_raw_text():
    parsed = BedrockRuntime.parse_framework_tool_output(
        "An error occurred while running the tool.",
        expected_tool_name="dividir",
    )

    assert parsed["ok"] is False
    assert parsed["kind"] == "object"
    assert parsed["tool_name"] == "dividir"
    assert isinstance(parsed["data"], dict)
    assert parsed["data"]["error_type"] == "NonEnvelopeToolOutput"


def test_parse_framework_tool_output_requires_valid_envelope_dict():
    parsed = BedrockRuntime.parse_framework_tool_output(
        {"result": 42},
        expected_tool_name="sumar",
    )

    assert parsed["ok"] is False
    assert parsed["tool_name"] == "sumar"
    assert parsed["data"]["error_type"] == "MalformedToolEnvelope"


def test_agent_contract_completion_aliases_are_normalized():
    from agentic_systems import AgentContract

    c1 = AgentContract(completion="when_contract_satisfied")
    c2 = AgentContract(completion="required_tools_ok")
    assert c1.completion == "when_required_tools_satisfied"
    assert c2.completion == "when_required_tools_satisfied"
