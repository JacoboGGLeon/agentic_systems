"""Textual-line semantics stay strict without conflating Markdown padding with text."""

import pytest
from scripts.semantic_e2e_application import (
    assert_semantic_response,
    looks_like_short_poem,
    build_semantic_cell,
    PLAIN_TEXT_INSTRUCTIONS,
    LITERAL_JUDGE_INSTRUCTIONS,
)
from agentic_systems import RunResult


@pytest.mark.parametrize("middle", [" 323", "\t323", "323\u00a0", "323.", "3 2 3"])
def test_visible_or_leading_format_changes_are_rejected(middle):
    answer = f"Quiet stars\n{middle}\nNumbers sing"
    assert not looks_like_short_poem(answer)
    assert not assert_semantic_response(
        RunResult(text=answer), {"name": "poetic_calculation"}
    ).ok
    assert looks_like_short_poem("Quiet stars\n323\nNumbers sing")

@pytest.mark.parametrize("padding", ["  ", "\t", " \t"])
def test_trailing_horizontal_padding_is_not_textual_content(padding):
    assert looks_like_short_poem(
        f"Quiet stars{padding}\n323{padding}\nNumbers sing{padding}"
    )


def test_literal_instructions_are_application_local():
    cell = build_semantic_cell("python-runtime", "native", model="python-runtime")
    orchestrator = next(a for a in cell.system.agents if a.name == "orchestrator_agent")
    assert PLAIN_TEXT_INSTRUCTIONS in orchestrator.instructions
    assert "trailing horizontal spaces or tabs" in LITERAL_JUDGE_INSTRUCTIONS


def test_literal_prompt_reaches_sdk_boundary_without_network(monkeypatch):
    import json
    import httpx
    from scripts.semantic_e2e_application import semantic_cases

    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder")
    captured = []

    def intercept(_client, request):
        captured.append(json.loads(request.read()))
        raise ConnectionError("offline transport interception")

    monkeypatch.setattr(httpx.Client, "_send_single_request", intercept)
    cell = build_semantic_cell("openai-runtime", "native", model="gpt-4.1-mini")
    case = next(
        c
        for c in semantic_cases("openai-runtime", "native")
        if c["name"] == "poetic_calculation"
    )
    result = cell.executable.run(case["input"])
    assert not result.ok
    assert captured
    for request in captured:
        assert PLAIN_TEXT_INSTRUCTIONS.strip() in request["messages"][0]["content"]
        assert request["messages"][1]["content"] == case["input"]
