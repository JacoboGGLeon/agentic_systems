from __future__ import annotations

import json

import pytest

from agentic_systems.cli import main


@pytest.mark.parametrize(
    ("argv", "workflow"),
    [
        (["tool", "run", "--value", "contract", "--json"], "tool"),
        (["skill", "inspect", "--json"], "skill"),
        (["agent", "run", "--value", "contract", "--json"], "agent"),
        (["system", "run", "--value", "contract", "--json"], "system"),
        (["graph", "run", "--value", "contract", "--json"], "graph"),
        (["environment", "run", "--value", "contract", "--json"], "environment"),
        (["eval", "run", "--value", "contract", "--json"], "eval"),
        (["matrix", "check", "--json"], "matrix"),
    ],
)
def test_cli_workflows_execute_public_api_scenarios(argv, workflow, capsys):
    assert main(argv) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["workflow"] == workflow
    assert payload["scenario"] == workflow
    assert payload["scenario_api_ids"]
    if workflow in {"tool", "agent", "system"}:
        assert payload["result"]["ok"] is True
    elif workflow == "skill":
        assert "cli_echo_skill" in payload["skill"]
    elif workflow == "graph":
        assert payload["state"] == {"value": "contract", "visited": True}
    elif workflow == "environment":
        assert payload["summary"]["ok"] is True
        assert payload["terminated"] is True
    elif workflow == "eval":
        assert payload["report"]["ok"] is True
        assert payload["report"]["total"] == 1
    else:
        assert payload["combination_count"] == 20
        assert payload["passed"] == 4
        assert payload["failed"] == 0
        assert payload["not_run"] == 16
        assert {
            (item["provider"], item["framework"])
            for item in payload["results"]
        } == {
            (provider, framework)
            for provider in (
                "python-runtime",
                "bedrock-runtime",
                "openai-runtime",
                "vllm-runtime",
                "ollama-runtime",
            )
            for framework in (
                "native",
                "langgraph",
                "openai-agents",
                "strands",
            )
        }


def test_cli_matrix_require_pass_uses_process_exit_semantics(capsys):
    assert main(
        [
            "matrix",
            "check",
            "--provider",
            "python-runtime",
            "--require-pass",
            "--json",
        ]
    ) == 0
    passed = json.loads(capsys.readouterr().out)
    assert passed["passed"] == 4
    assert passed["not_run"] == 0

    assert (
        main(
            [
                "matrix",
                "check",
                "--provider",
                "ollama-runtime",
                "--require-pass",
                "--json",
            ]
        )
        == 1
    )
    not_run = json.loads(capsys.readouterr().out)
    assert not_run["not_run"] == 4

    assert main(["matrix", "check", "--framework", "langgraph", "--json"]) == 0
    framework = json.loads(capsys.readouterr().out)
    assert framework["combination_count"] == 5
    assert {item["framework"] for item in framework["results"]} == {"langgraph"}
