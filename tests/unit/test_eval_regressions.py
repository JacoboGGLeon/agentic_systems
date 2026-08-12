import pytest

from agentic_systems import (
    RunResult,
)
from agentic_systems.evals import run_eval


def test_eval_report_pass_and_fail_paths():
    class EvalAgent:
        def __init__(self, result):
            self.result = result

        def run_sync(self, input, mode="eval", config=None):
            return self.result

    passing = run_eval(
        EvalAgent(RunResult(text="hello world", data={"risk": "low"})),
        [
            {
                "name": "ok",
                "input": {"x": 1},
                "expected": {
                    "text_contains": "world",
                    "data_contains": {"risk": "low"},
                    "must_call": [],
                    "expected_tool_outputs": {},
                },
            }
        ],
    )
    assert passing.to_dict()["passed"] == 1
    assert passing.raise_if_failed() is passing

    failing = run_eval(
        EvalAgent(RunResult(text="nope", data={"risk": "high"})),
        [
            {
                "input": "x",
                "expected": {
                    "text_contains": "missing",
                    "data_contains": {"risk": "low"},
                },
            }
        ],
    )
    assert failing.ok is False
    with pytest.raises(AssertionError, match="case_1"):
        failing.raise_if_failed()
