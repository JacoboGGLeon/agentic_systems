"""Replay actual Qwen failures through both SDKs, without inference."""
import importlib
import json
from pathlib import Path

import pytest
import agentic_systems as toolkit
from agentic_systems._contracts import _check_output
from examples.common_graph.application import CASE, build_system, check_result


FRAMEWORKS = ("openai-agents", "strands")
FIXTURES = json.loads((Path(__file__).parent / "fixtures/bedrock_qwen_fenced.json").read_text(encoding="utf-8"))
CONTRACT = {"output_schema": {"type": "object", "required": ["value"],
    "additionalProperties": False, "properties": {"value": {"type": "integer"}}}}


def adapter(framework):
    return importlib.import_module("agentic_systems._engine.integrations.adapters." + framework.replace("-", "_"))


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_original_qwen_fenced_response_through_real_sdk(monkeypatch, framework):
    from botocore.client import BaseClient
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "offline-test-bearer")
    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    from agents import set_tracing_disabled
    set_tracing_disabled(True)
    raw = next(row["raw_text"] for row in FIXTURES if row["framework"] == framework)
    calls = []

    def converse(client, operation, arguments):
        assert client.meta.service_model.service_name == "bedrock-runtime"
        assert operation == "Converse"
        assert arguments["modelId"] == "qwen.qwen3-32b-v1:0"
        calls.append(arguments)
        return {"output": {"message": {"role": "assistant", "content": [{"text": raw}]}},
                "stopReason": "end_turn", "usage": {"inputTokens": 487, "outputTokens": 97, "totalTokens": 584},
                "metrics": {"latencyMs": 1}, "ResponseMetadata": {"RequestId": "offline-replay", "HTTPStatusCode": 200}}

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)
    reasoner = toolkit.runtime(provider="bedrock-runtime", model="qwen.qwen3-32b-v1:0", region="us-east-2",
        api_key="offline-test-bearer", max_tokens=1024, max_retries=0, max_tool_calls=0, max_turns=2)
    program = build_system(framework, reasoner=reasoner, interactive=True).compile()
    waiting = program.run(CASE, timeout_s=40)
    assert waiting.status == "paused", waiting.to_dict()
    final = program.resume(waiting, True)
    assert check_result(final), final.to_dict()
    assert final.data["status"] == "approved"
    assert len(calls) == 1  # Resume must not repeat a completed model invocation.
    actors = [node for node in final.walk() if node.model == "qwen.qwen3-32b-v1:0" and not node.children]
    assert len(actors) == 1
    assert actors[0].text.strip() == raw.strip()  # Original evidence is never rewritten.
    assert actors[0].usage["inference_requests"] == 1
    assert actors[0].raw_responses
    assert toolkit.RunResult(**final.to_dict()).check_invariants().ok


@pytest.mark.parametrize("framework", FRAMEWORKS)
@pytest.mark.parametrize("text", [
    '{"value": 7}', '  {"value": 7}\n',
    '```json\n{"value": 7}\n```', '```\n{"value": 7}\n```',
    '\n  ```JSON \r\n{"value": 7}\r\n``` \n',
])
def test_single_document_json_formatting_keeps_contract(framework, text):
    data = adapter(framework)._output_data(text, text)
    checked = _check_output(toolkit.RunResult(text=text, data=data), CONTRACT)
    assert checked.ok and checked.data == {"value": 7}
    assert checked.text == text


@pytest.mark.parametrize("framework", FRAMEWORKS)
@pytest.mark.parametrize("text", [
    'Here is JSON:\n```json\n{"value": 7}\n```',
    '```json\n{"value": 7}\n```\nDone.',
    '```json\n{"value": 7}\n```\n```json\n{"value": 8}\n```',
    '```json\n{"value": 7}',
    '```python\n{"value": 7}\n```',
    '```json\n{"value": 7,}\n```',
    '```json\n{"value": 7} {"value": 8}\n```',
    '```json\n[7]\n```',
    '```json\n{"other": 7}\n```',
    '```json\n{"value": "7"}\n```',
    '```json\n{"value": 7, "extra": true}\n```',
])
def test_ambiguous_malformed_or_schema_invalid_output_still_fails(framework, text):
    data = adapter(framework)._output_data(text, text)
    checked = _check_output(toolkit.RunResult(text=text, data=data), CONTRACT)
    assert not checked.ok
    assert checked.validation["issues"]
    assert checked.text == text


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_structured_business_data_is_authoritative(framework):
    raw = '```json\n{"value": 7}\n```'
    payload = {"text": raw}
    assert adapter(framework)._output_data(payload, raw) == payload
    result = _check_output(toolkit.RunResult(text=raw, data=payload), CONTRACT)
    assert not result.ok  # Never recover a valid-looking value from failed business data.
