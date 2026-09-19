from types import SimpleNamespace
import pytest
import scripts.claim_eval_adapter as adapter


@pytest.mark.parametrize(
    "status,score", [("pass", 1.0), ("fail", 0.0), ("unknown", 0.0)]
)
def test_eval_adapter_preserves_unknown_as_nonpassing(monkeypatch, status, score):
    report = {
        "execution_ok": True,
        "verdict": {"grounding": status, "clarity": True, "records": []},
    }
    monkeypatch.setattr(
        adapter, "build", lambda *args: SimpleNamespace(evaluate=lambda *args: report)
    )
    judge = adapter.make_claim_judge("test", "test", "test")
    result = judge.run(
        {
            "case": {"input": {"evidence": []}},
            "candidate": {"answer": {"text": "fixture"}},
        }
    )
    assert result.data["criteria"]["grounding"] == score
    assert judge.runs == [report]
