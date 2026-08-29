from __future__ import annotations

import pytest

pytest.importorskip("a2a")

from semantic_challenges.strands_protocol_graph.application import (
    NativeProtocolJudge,
    ProtocolChallenge,
)


MCP_TOKEN = "MCP-TEST-EVIDENCE-7F3A"
A2A_TOKEN = "A2A-TEST-EVIDENCE-91C2"


def test_protocol_challenge_executes_real_mcp_a2a_strands_and_langgraph() -> None:
    with ProtocolChallenge(
        "python-runtime",
        model="python-runtime",
        mcp_token=MCP_TOKEN,
        a2a_token=A2A_TOKEN,
    ) as challenge:
        result = challenge.run(
            {
                "steps": [
                    {
                        "tool": "fetch_mcp_evidence",
                        "input": {},
                    },
                    {
                        "tool": "fetch_a2a_evidence",
                        "input": {},
                    },
                ]
            }
        )

    nodes = list(result.walk())
    assert result.ok, result.errors
    assert result.engine == "python-runtime"
    assert result.meta["framework_adapter"] == "langgraph"
    assert result.meta["graph_native_type"] == "CompiledStateGraph"
    assert len(nodes) == 2
    candidate = nodes[1]
    assert candidate.meta["framework_adapter"] == "strands"
    assert [event.name for event in candidate.tool_events] == [
        "fetch_mcp_evidence",
        "fetch_a2a_evidence",
    ]
    assert candidate.tool_events[0].output == {
        "protocol": "mcp",
        "token": MCP_TOKEN,
        "status": "verified",
    }
    assert candidate.tool_events[0].input == {}
    assert candidate.tool_events[1].input == {}
    assert A2A_TOKEN in str(candidate.tool_events[1].output)
    assert "a2a" in str(candidate.tool_events[1].output).lower()
    for node in nodes:
        node.check_invariants().raise_if_failed()


def test_native_judge_scores_complete_public_evidence() -> None:
    request = {
        "case": {
            "expected": {
                "text_contains": [MCP_TOKEN, A2A_TOKEN],
                "tool_path": ["fetch_mcp_evidence", "fetch_a2a_evidence"],
                "tool_output_contains": {
                    "fetch_mcp_evidence": {
                        "protocol": "mcp",
                        "token": MCP_TOKEN,
                    },
                    "fetch_a2a_evidence": {
                        "protocol": "a2a",
                        "token": A2A_TOKEN,
                    },
                },
                "execution_path": [
                    {"provider": "openai-runtime", "framework": "langgraph"},
                    {"provider": "openai-runtime", "framework": "strands"},
                ],
            },
        },
        "candidate": {
            "executions": [
                {
                    "runtime": {
                        "provider": "openai-runtime",
                        "framework": "langgraph",
                    },
                    "answer": {
                        "text": (f"MCP verified {MCP_TOKEN}. A2A verified {A2A_TOKEN}.")
                    },
                    "tools": [],
                },
                {
                    "runtime": {
                        "provider": "openai-runtime",
                        "framework": "strands",
                    },
                    "answer": {"text": "verified"},
                    "tools": [
                        {
                            "name": "fetch_mcp_evidence",
                            "output": {"protocol": "mcp", "token": MCP_TOKEN},
                        },
                        {
                            "name": "fetch_a2a_evidence",
                            "output": {"protocol": "a2a", "token": A2A_TOKEN},
                        },
                    ],
                },
            ]
        },
    }
    judged = NativeProtocolJudge().run(request)
    assert judged.ok, judged.errors
    assert [event.name for event in judged.tool_events] == ["certify_protocol_episode"]
    event_output = judged.tool_events[0].output
    payload = event_output.get("data", event_output)
    assert payload["score"] == 1.0
    assert payload["failed_criteria"] == []
    assert all(score == 1.0 for score in payload["criteria"].values())
