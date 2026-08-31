import os
from pathlib import Path

import pytest

from agentic_systems import AgentContract, AgenticSystem, RunResult
from agentic_systems.tools import ToolEvent
from agentic_systems.errors import ToolContractError


def build_system(strict=True):
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="qwen.qwen3-32b-v1:0", region="us-east-1", strict=strict)


class FakeBedrockRuntime:
    def __init__(self):
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        messages = kwargs.get("messages", [])
        has_tool_result = any(
            "toolResult" in block
            for message in messages
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        has_synthesis = any(
            "BedrockRuntime final synthesis instruction" in block.get("text", "")
            for message in messages
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        if kwargs.get("toolConfig") and not has_tool_result:
            return {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"toolUse": {"toolUseId": "tool-1", "name": "sumar", "input": {"a": 17, "b": 25}}}
                        ],
                    }
                },
                "stopReason": "tool_use",
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                "ResponseMetadata": {"RequestId": "r1", "HTTPStatusCode": 200},
            }
        text = "Resultado final: 42" if has_tool_result or has_synthesis else "Respuesta directa controlada"
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 8, "outputTokens": 4, "totalTokens": 12},
            "ResponseMetadata": {"RequestId": "r2", "HTTPStatusCode": 200},
        }



def test_system_can_register_tool_and_create_agent():
    system = build_system()

    @system.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos números."""
        return {"result": a + b}

    agent = system.agent(
        name="math_agent",
        instructions="Use sumar when arithmetic is requested.",
        tools=["sumar"],
        contract={"must_call": ["sumar"]},
    )

    assert "sumar" in system.tool_names
    assert agent.name == "math_agent"
    assert agent.tools == ("sumar",)
    assert system.inspect()["ok"] is True


def test_strict_tool_contract_requires_dict_annotation():
    system = build_system()

    with pytest.raises(ToolContractError):
        @system.tool
        def keywords(text: str) -> list[str]:
            """Invalid for AgenticSystem strict public contract."""
            return text.split()


def test_runtime_tool_contract_error_becomes_failed_envelope():
    system = build_system()

    @system.tool
    def keywords(text: str) -> dict:
        """Wrong runtime value despite correct annotation."""
        return text.split()  # type: ignore[return-value]

    envelope = system.execute_tool("keywords", {"text": "Bedrock agents"})
    assert envelope.ok is False
    assert envelope.data["error_type"] in {"TypeError", "ToolContractError"}
    assert "must return dict" in envelope.data["message"]


def test_agent_run_uses_bedrock_engine_with_fake_client():
    system = build_system()
    system._runtime.runtime = FakeBedrockRuntime()

    @system.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos números."""
        return {"result": a + b}

    agent = system.agent(
        name="math_agent",
        instructions="Always use sumar.",
        tools=["sumar"],
        contract={"must_call": ["sumar"], "completion": "default"},
        policy={"tool_choice": "required"},
    )

    result = agent.run_sync("Suma 17 y 25", mode="eval")
    assert isinstance(result, RunResult)
    assert result.text == "Resultado final: 42"
    assert result.ok is True
    assert [event.name for event in result.tool_events] == ["sumar"]
    assert result.tool_events[0].output["data"] == {"result": 42}
    assert result.trace()["trace_schema_version"] == "agentic_systems.trace.v1"


def test_bedrock_agent_with_no_tools_does_not_inherit_system_tools():
    system = build_system()
    fake_runtime = FakeBedrockRuntime()
    system._runtime.runtime = fake_runtime

    @system.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos números."""
        return {"result": a + b}

    agent = system.agent(
        name="grounded_agent",
        instructions="Respond without executable capabilities.",
        tools=[],
        policy={"max_tool_calls": 0},
    )

    result = agent.run_sync("Describe the evidence.", mode="eval")

    assert result.ok is True
    assert result.tool_events == []
    assert "toolConfig" not in fake_runtime.calls[0]


def test_agent_as_node_returns_partial_update():
    system = build_system()
    system._runtime.runtime = FakeBedrockRuntime()

    @system.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos números."""
        return {"result": a + b}

    agent = system.agent(
        name="math_agent",
        instructions="Use sumar.",
        tools=["sumar"],
        policy={"tool_choice": "required"},
    )
    node = agent.as_node(input="prompt", output="answer", trace="trace")
    update = node({"prompt": "Suma 17 y 25", "memory": ["preserve"]})

    assert set(update) == {"answer", "trace"}
    assert update["answer"] == "Resultado final: 42"
    assert update["trace"]["tool_event_count"] == 1
    assert "memory" not in update


def test_result_validate_contract_detects_missing_tool():
    result = RunResult(text="ok", tool_events=[ToolEvent(id="1", name="a", ok=True)])
    validation = result.validate(AgentContract(must_call=["b"]))
    assert validation.ok is False
    assert validation.issues[0].code == "missing_required_tool"


def test_toolkit_and_skill_loading():
    system = build_system()
    skill_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "skills" / "demo"
    loaded = system.load_skill(skill_path)
    assert loaded.manifest.name == "demo"
    assert "sumar" in system.tool_names
    assert "dividir" in system.tool_names
    assert loaded.manifest.tools == ["sumar", "restar", "multiplicar", "dividir", "number_to_text", "read_md"]
