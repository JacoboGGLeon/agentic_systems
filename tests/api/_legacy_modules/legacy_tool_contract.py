import os
from dataclasses import dataclass

from pydantic import BaseModel

from agentic_systems.engines.bedrock_runtime import BedrockRuntime, ToolEnvelope


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
        """Suma dos números."""
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
        """Divide dos números."""
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


def test_openai_history_conversion_marks_non_envelope_output_as_tool_error():
    runtime = build_runtime()

    messages, _ = runtime._openai_input_to_bedrock_messages(
        [
            {
                "type": "function_call",
                "call_id": "call_1",
                "name": "dividir",
                "arguments": "{}",
            },
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": "An error occurred while running the tool.",
            },
        ]
    )

    assert messages[0]["role"] == "assistant"
    assert messages[1]["role"] == "user"
    tool_result = messages[1]["content"][0]["toolResult"]
    assert tool_result["status"] == "error"
    payload = tool_result["content"][0]["json"]
    assert payload["tool_name"] == "dividir"
    assert payload["ok"] is False
    assert payload["data"]["error_type"] == "NonEnvelopeToolOutput"


def test_coerce_framework_tool_arguments_accepts_dict_and_json_string():
    assert BedrockRuntime._coerce_framework_tool_arguments({"a": 1}) == {"a": 1}
    assert BedrockRuntime._coerce_framework_tool_arguments('{"a": 1}') == {"a": 1}
    assert BedrockRuntime._coerce_framework_tool_arguments(None) == {}


def test_openai_function_tool_accepts_dict_raw_args_without_json_string_assumption():
    import asyncio
    import json
    pytest = __import__("pytest")
    pytest.importorskip("agents")

    runtime = build_runtime()

    @runtime.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos números."""
        return {"result": a + b}

    tool = runtime.as_openai_runtime_tools(["sumar"])[0]
    raw = asyncio.run(tool.on_invoke_tool(None, {"a": 17, "b": 25}))
    parsed = json.loads(raw)

    assert parsed["ok"] is True
    assert parsed["tool_name"] == "sumar"
    assert parsed["kind"] == "object"
    assert parsed["data"] == {"result": 42}


def test_contains_subset_uses_substring_for_nested_strings():
    actual = {"content": "# Tabla\n| 2 | azul |\n"}
    expected = {"content": "| 2 | azul |"}
    assert BedrockRuntime._contains_subset(actual, expected) is True


def test_openai_strict_json_schema_adds_additional_properties_false():
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "nested": {"type": "object", "properties": {"x": {"type": "string"}}},
        },
        "required": ["a"],
    }
    strict = BedrockRuntime._ensure_openai_strict_json_schema(schema)
    assert strict["additionalProperties"] is False
    assert strict["properties"]["nested"]["additionalProperties"] is False


def test_openai_unresolved_failed_tools_from_input_detects_recovered_failure():
    runtime = build_runtime()
    failed = runtime.to_envelope(
        {"error_type": "ValidationError", "message": "missing args"},
        tool_name="restar",
        ok=False,
    ).model_dump_json()
    ok = runtime.to_envelope(
        {"operation": "restar", "result": 21},
        tool_name="restar",
        ok=True,
    ).model_dump_json()

    unresolved_first = runtime._openai_unresolved_failed_tools_from_input([
        {"type": "function_call", "call_id": "c1", "name": "restar", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c1", "output": failed},
    ])
    assert len(unresolved_first) == 1
    assert unresolved_first[0]["tool_name"] == "restar"

    unresolved_after_repair = runtime._openai_unresolved_failed_tools_from_input([
        {"type": "function_call", "call_id": "c1", "name": "restar", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c1", "output": failed},
        {"type": "function_call", "call_id": "c2", "name": "restar", "arguments": '{"a": 30, "b": 9}'},
        {"type": "function_call_output", "call_id": "c2", "output": ok},
    ])
    assert unresolved_after_repair == []


def test_openai_history_conversion_skips_orphan_tool_outputs():
    runtime = build_runtime()
    ok = runtime.to_envelope(
        {"operation": "sumar", "result": 42},
        tool_name="sumar",
        ok=True,
    ).model_dump_json()

    messages, extra_system = runtime._openai_input_to_bedrock_messages(
        [
            {"role": "user", "content": "calcula"},
            {"type": "function_call_output", "call_id": "orphan", "output": ok},
        ]
    )

    assert all(
        "toolResult" not in block
        for message in messages
        for block in message.get("content", [])
    )
    assert any("orphan" in block.get("text", "") for block in extra_system)


def test_agent_contract_completion_aliases_are_normalized():
    from agentic_systems import AgentContract

    c1 = AgentContract(completion="when_contract_satisfied")
    c2 = AgentContract(completion="required_tools_ok")
    assert c1.completion == "when_required_tools_satisfied"
    assert c2.completion == "when_required_tools_satisfied"
