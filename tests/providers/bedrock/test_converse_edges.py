from __future__ import annotations


from agentic_systems.providers.bedrock.converse import _ConverseMixin
from agentic_systems.providers.bedrock.models import BedrockRunResult
from agentic_systems.providers.bedrock.tools import _ToolsMixin


class RuntimeAPI:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class ConverseRuntime(_ConverseMixin, _ToolsMixin):
    model_id = "model-default"
    max_tokens_default = 80
    temperature_default = 0.1

    def __init__(self, response=None):
        self._tools = {}
        self.runtime = RuntimeAPI(response if response is not None else {})


def test_converse_forwards_all_optional_fields_and_records_duration():
    runtime = ConverseRuntime({"output": {}})
    response = runtime.converse(
        messages=[{"role": "user", "content": [{"text": "hi"}]}],
        system=[{"text": "system"}],
        tools=[{"toolSpec": {"name": "lookup"}}],
        tool_choice={"any": {}},
        model_id="model-explicit",
        max_tokens=10,
        temperature=0.0,
        top_p=0.8,
        stop_sequences=["STOP"],
    )
    call = runtime.runtime.calls[0]
    assert call["modelId"] == "model-explicit"
    assert call["inferenceConfig"] == {
        "maxTokens": 10,
        "temperature": 0.0,
        "topP": 0.8,
        "stopSequences": ["STOP"],
    }
    assert call["toolConfig"]["toolChoice"] == {"any": {}}
    assert response["agentic_systems"]["client_duration_ms"] >= 0

    non_mapping = ConverseRuntime("raw")
    assert non_mapping.converse(messages=[]) == "raw"


def test_tool_names_maps_specs_and_choice_contracts(monkeypatch):
    runtime = ConverseRuntime()

    @runtime.tool(name="customer.lookup")
    def lookup(value: int):
        """Lookup."""
        return value

    @runtime.tool(name="other")
    def other(value: int):
        """Other."""
        return value

    assert runtime.bedrock_safe_tool_name("").startswith("tool_")
    assert runtime.bedrock_safe_tool_name("safe_name") == "safe_name"
    sanitized = runtime.bedrock_safe_tool_name("customer.lookup")
    assert sanitized.startswith("customer_lookup_")

    canonical, reverse = runtime._bedrock_tool_name_maps()
    assert reverse[canonical["customer.lookup"]] == "customer.lookup"
    specs = runtime.as_bedrock_tools(canonical_to_bedrock=canonical)
    assert specs[0]["toolSpec"]["name"] == canonical["customer.lookup"]

    monkeypatch.setattr(runtime, "bedrock_safe_tool_name", lambda name: "same")
    canonical, _ = runtime._bedrock_tool_name_maps()
    assert canonical["customer.lookup"] == "same"
    assert canonical["other"].startswith("same_")

    assert runtime._map_tool_choice(None) == {"auto": {}}
    assert runtime._map_tool_choice("required") == {"any": {}}
    assert runtime._map_tool_choice("lookup") == {"tool": {"name": "lookup"}}
    assert runtime._map_tool_choice(3) == {"auto": {}}
    assert runtime._tool_choice_for_turn("any", turn_index=1) == {"auto": {}}


def test_assistant_content_sanitization_preserves_valid_and_records_invalid():
    runtime = ConverseRuntime()
    safe, valid, invalid = runtime._sanitize_bedrock_assistant_content(
        [
            None,
            {"text": "hello"},
            {"toolUse": {"toolUseId": "c1", "name": "lookup", "input": "raw"}},
            {"toolUse": {"toolUseId": "", "name": "", "input": "bad"}},
            {"toolUse": None},
        ]
    )
    assert safe[0] == {"text": "hello"}
    assert valid == [{"toolUseId": "c1", "name": "lookup", "input": {"value": "raw"}}]
    assert len(invalid) == 2
    assert invalid[0].tool_input == {"value": "bad"}
    assert invalid[0].tool_output["data"]["error_type"] == "InvalidBedrockToolUse"


def test_compact_metadata_and_print_result(capsys):
    compact = ConverseRuntime._compact_response_metadata({})
    assert compact == {
        "request_id": None,
        "http_status_code": None,
        "usage": {},
        "stop_reason": None,
        "service_latency_ms": None,
        "client_duration_ms": None,
    }
    result = BedrockRunResult(final_text="done", messages=[])
    ConverseRuntime.print_run_result(result, mode="full")
    assert '"final_text": "done"' in capsys.readouterr().out


def test_run_direct_uses_the_direct_runner():
    runtime = ConverseRuntime({"output": {"message": {"content": [{"text": "done"}]}}})
    assert runtime.run_direct("hello", max_turns=1).final_text == "done"
