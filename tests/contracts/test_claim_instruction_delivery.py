"""Actual library execution with a controlled completion boundary, no network."""

import copy
import json
from types import SimpleNamespace

import pytest

from agentic_systems.system import AgenticSystem
from scripts.claim_evaluator import build


@pytest.mark.parametrize("provider", ["openai-runtime", "ollama-runtime"])
@pytest.mark.parametrize("framework", ["native", "langgraph"])
def test_each_stage_delivers_its_own_instructions_and_input(
    monkeypatch, provider, framework
):
    import agentic_systems.providers.openai_runtime as openai_provider
    import agentic_systems.providers.ollama_runtime as ollama_provider

    agents = {}
    requests = []
    original = AgenticSystem.agent

    def capture_agent(self, **kwargs):
        agent = original(self, **kwargs)
        agents[agent.name] = agent
        return agent

    def create(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        tools = kwargs.get("tools")
        if not tools:
            message = SimpleNamespace(content="Recorded.", tool_calls=[])
        else:
            instruction = kwargs["messages"][0]["content"]
            names = [
                name
                for name, agent in agents.items()
                if agent.instructions == instruction
            ]
            assert len(names) == 1, "Lost, mixed or replaced stage instructions"
            stage = names[0]
            payloads = {
                "partition": {"fragments": ["A verifiable claim."]},
                "audit_partition": {"coherent": True},
                "factuality": {"factual": True},
                "support": {
                    "all_assertions_supported": True,
                    "evidence_ids": ["record-a"],
                },
                "contradiction": {
                    "any_assertion_contradicted": False,
                    "evidence_ids": [],
                },
                "clarity": {"clear": True},
            }
            tool = tools[0]["function"]
            assert tool["name"] == agents[stage].available_tools()[0].name
            message = SimpleNamespace(
                content="",
                tool_calls=[
                    SimpleNamespace(
                        id=f"call-{len(requests)}",
                        type="function",
                        function=SimpleNamespace(
                            name=tool["name"], arguments=json.dumps(payloads[stage])
                        ),
                    )
                ],
            )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    sdk = SimpleNamespace(OpenAI=lambda **kwargs: client)
    monkeypatch.setattr(AgenticSystem, "agent", capture_agent)
    monkeypatch.setattr(openai_provider, "_openai_module", lambda: sdk)
    monkeypatch.setattr(ollama_provider, "_openai_module", lambda: sdk)
    evidence = [{"id": "record-a", "ok": True}]
    result = build(provider, framework, "offline-model").evaluate(
        "A verifiable claim.", evidence
    )
    assert result["execution_ok"], result.get("failure")
    assert result["verdict"]["grounding"] == "pass"
    first_requests = [request for request in requests if request.get("tools")]
    assert len(first_requests) == 6
    assert [request["messages"][0]["content"] for request in first_requests] == [
        agents[name].instructions
        for name in (
            "partition",
            "audit_partition",
            "factuality",
            "support",
            "contradiction",
            "clarity",
        )
    ]
    factuality = json.loads(first_requests[2]["messages"][1]["content"])
    assert factuality == {"target_text": "A verifiable claim."}
    for request in first_requests[3:5]:
        assert request["messages"][0]["role"] == "system"
        assert request["messages"][1]["role"] == "user"
        assert json.loads(request["messages"][1]["content"]) == {
            "target_text": "A verifiable claim.",
            "reference_context": [],
            "observed_records": evidence,
        }
