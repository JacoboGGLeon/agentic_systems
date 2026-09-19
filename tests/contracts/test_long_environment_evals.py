import copy
import pytest
from scripts.long_environment_control import build_control, run_episode
from scripts.long_environment_evals import evaluate_saved
import agentic_systems as toolkit


class ApprovingControlJudge:
    def run(self, request, **kwargs):
        assert len(request["case"]["input"]["evidence"]) > 0
        assert request["candidate"]["answer"]["text"]
        return toolkit.RunResult(
            ok=True,
            data={
                "criteria": {"grounding": 1.0, "clarity": 1.0},
                "score": 1.0,
                "findings": [],
                "rationale": "Control fixture, not model inference",
            },
        )


@pytest.fixture(scope="module")
def evidence():
    env, observed, _ = build_control()
    return run_episode(env), observed


def test_original_long_episode_passes_deterministic_evals(evidence):
    report = evaluate_saved(*evidence)
    assert report["passed"]
    assert not report["semantic_evaluated"]
    assert len(report["reports"]) == 7


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("duplicate", "duplicate_event_identity"),
        ("parent", "parent_mismatch"),
        ("output", "tool_output_mismatch"),
        ("omission", "tool_count_mismatch"),
    ],
)
def test_corrupted_long_evidence_fails_for_specific_reason(evidence, mutation, code):
    history, observed = copy.deepcopy(evidence)
    run = history[0]["graph_state"]["run"]
    if mutation == "duplicate":
        run["tools"][1]["id"] = run["tools"][0]["id"]
    elif mutation == "parent":
        run["children"][0]["execution"]["parent_execution_id"] = "foreign"
    elif mutation == "output":
        run["tools"][0]["output"]["value"] = -1
    else:
        run["tools"].pop()
    report = evaluate_saved(history, observed)
    assert not report["passed"]
    assert code in str(report["reports"][0])


def test_approving_judge_cannot_override_corrupted_evidence(evidence):
    history, observed = copy.deepcopy(evidence)
    history[0]["graph_state"]["run"]["tools"][0]["output"]["value"] = -1
    result = evaluate_saved(history, observed, judge=ApprovingControlJudge())
    assert not result["passed"]
    assert "tool_output_mismatch" in str(result["reports"][0])
