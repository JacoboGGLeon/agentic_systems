"""Bedrock must preserve explicit nulls and reject missing required fields."""

import json

from agentic_systems._engine.engines.bedrock import _input_to_prompt
from agentic_systems._engine.providers.bedrock.converse import _ConverseMixin
from agentic_systems._engine.providers.bedrock.tools import _ToolsMixin
from examples.applications.data_quality.example import profile_rows, sample


def test_null_is_preserved_in_bedrock_prompt_and_tool_use():
    assert json.loads(_input_to_prompt(sample)) == sample
    raw = [
        {"toolUse": {"toolUseId": "call-1", "name": "profile_rows", "input": sample}}
    ]
    content, uses, invalid = _ConverseMixin._sanitize_bedrock_assistant_content(
        None, raw
    )
    assert not invalid and uses[0]["input"] == sample and content == raw


def test_bedrock_tool_execution_does_not_invent_a_missing_null():
    class LocalTools(_ToolsMixin):
        def __init__(self):
            self._tools = {}

    tools = LocalTools()
    tools.tool(profile_rows._function, name="profile_rows")
    good = tools.execute_tool("profile_rows", sample)
    assert good.ok and good.data == {
        "rows": 2,
        "duplicate_ids": 1,
        "missing_amounts": 1,
    }
    bad = tools.execute_tool("profile_rows", {"rows": [{"id": 1}]})
    assert not bad.ok and bad.data["error_type"] == "ValidationError"


def test_botocore_document_parser_preserves_null_in_converse_response():
    from botocore.session import get_session
    from botocore.parsers import create_parser

    service = get_session().get_service_model("bedrock-runtime")
    operation = service.operation_model("Converse")
    body = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "call-1",
                            "name": "profile_rows",
                            "input": sample,
                        }
                    }
                ],
            }
        },
        "stopReason": "tool_use",
        "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        "metrics": {"latencyMs": 1},
    }
    parsed = create_parser(service.metadata["protocol"]).parse(
        {"body": json.dumps(body).encode(), "headers": {}, "status_code": 200},
        operation.output_shape,
    )
    assert parsed["output"]["message"]["content"][0]["toolUse"]["input"] == sample
