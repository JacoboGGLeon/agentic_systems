from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import agentic_systems as toolkit
from agentic_systems.tools import ToolEvent


def test_live_runner_evaluates_each_observation_once_and_separates_usage(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/validate_conversation_live.py"
    spec = spec_from_file_location("studio_evaluation_runner_test", path)
    runner = module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert runner._episode_usage(
        {"scheduler.timed_out": False}, {"scheduler.timed_out": True}
    )["scheduler.timed_out"] is True
    calls = []

    def candidate_run(prompt, history):
        calls.append(prompt)
        return toolkit.RunResult(
            ok=True,
            text="Observed response",
            engine="python-runtime",
            model="control",
            usage={
                "requests": 1,
                "input_tokens": 5,
                "output_tokens": 2,
                "total_tokens": 7,
            },
        )

    class Judge:
        last_result = None

        def run(self, request, **kwargs):
            scores = {name: 1.0 for name in toolkit.JudgeRubric().criteria}
            scores["request_fulfillment"] = 0.0
            payload = {
                "criteria": scores,
                "score": 0.8,
                "findings": [
                    {
                        "criterion": "request_fulfillment",
                        "evidence": "The candidate did not fulfill the task.",
                    }
                ],
            }
            self.last_result = toolkit.RunResult(
                ok=True,
                text="Judgment recorded",
                engine="python-runtime",
                usage={
                    "requests": 1,
                    "input_tokens": 8,
                    "output_tokens": 3,
                    "total_tokens": 11,
                },
                tool_events=[
                    ToolEvent(
                        id="judgment",
                        name="record_conversation_judgment",
                        input={},
                        output=payload,
                        ok=True,
                    )
                ],
            )
            return self.last_result

    monkeypatch.setattr(
        runner,
        "ConversationConfig",
        SimpleNamespace(
            from_environment=lambda **kwargs: SimpleNamespace(model="control")
        ),
    )
    monkeypatch.setattr(
        runner,
        "build_conversational_system",
        lambda config: SimpleNamespace(run=candidate_run),
    )
    monkeypatch.setattr(runner, "build_conversation_judge", lambda config: Judge())
    monkeypatch.setattr(runner, "_assert_live_result", lambda *args, **kwargs: None)
    report = runner._run_conversation("python-runtime", long=False)
    assert len(calls) == 2  # Eval observes; it must not run the candidate again.
    assert not report["ok"]
    assert len(report["validation_errors"]) == 2
    assert report["usage_totals"]["total_tokens"] == 14
    assert report["judge_usage_totals"]["total_tokens"] == 22
    assert report["episode_usage_totals"]["total_tokens"] == 36
    assert report["episode_usage_totals"]["scheduler.timed_out"] is False
    for turn in report["turns"]:
        assert turn["evaluation"]["deterministic_validation"]["ok"]
        assert not turn["semantic_validation"]["ok"]
        assert "Observed response" in turn["human_result"]
        assert turn["judge_execution"]
        assert turn["judge_lineage"]
