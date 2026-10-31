"""Text presentation must not discard a Python Tool's business fields."""
import pytest
import agentic_systems as toolkit


@pytest.mark.parametrize("framework", ("native", "openai-agents", "strands"))
def test_business_text_and_nested_evidence_are_preserved(framework):
    expected = {
        "text": "observed response", "history_turns": 0, "answer": "business answer",
        "evidence": {"text": "nested evidence", "amount": None}, "ok": False,
    }

    @toolkit.tool
    def respond(value: int) -> dict:
        assert value == 3
        return expected

    actor = toolkit.Agent(
        "text_operator", runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(framework),
        skills=(toolkit.skill(name="reply", tools=(respond,)),),
    )
    result = actor.run({"value": 3})
    assert result.ok and result.data == expected, result.to_dict()
    assert result.check_invariants().ok
    assert result.usage.get("inference_requests", 0) == 0
