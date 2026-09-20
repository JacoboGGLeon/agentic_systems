import json
import pytest
from scripts.long_environment_control import build_control, run_episode, SPEC


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_long_environment_routes_lineage_and_reset(framework):
    env, observed, runs = build_control(framework)
    history = run_episode(env)
    assert len(history) == SPEC["steps"]
    assert env.memory["value"] == 7 * sum(range(1, 12))
    assert len(observed) == 77
    assert all(run.ok and len(run.children) == 9 for run in runs)
    assert all(len(run.normalized()["tools"]) == 11 for run in runs)
    for run in runs:
        normalized = run.normalized()
        assert all(
            child["execution"]["parent_execution_id"]
            == normalized["execution"]["execution_id"]
            for child in normalized["children"]
        )
        assert len({event["id"] for event in normalized["tools"]}) == 11
    retained = list(env.history)
    frozen = json.dumps([entry.to_dict() for entry in retained])
    for step, run in enumerate(runs):
        events = run.normalized()["tools"]
        actual = [item for item in observed if item["step"] == step]
        # Sibling tools are independent: compare multiplicity, not SDK completion order.
        assert sorted(
            (event["name"], event["input"], event["ok"]) for event in events
        ) == sorted(
            (item["name"], {"value": item["value"], "step": item["step"]}, item["ok"])
            for item in actual
        )
    run_episode(env)
    assert env.memory["value"] == 462
    assert len(observed) == 154
    assert json.dumps([entry.to_dict() for entry in retained]) == frozen
    assert len({run.normalized()["execution"]["execution_id"] for run in runs}) == 14


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_long_environment_failure_is_preserved(framework):
    env, observed, runs = build_control(framework, fail_step=3)
    run_episode(env)
    assert not runs[3].ok
    assert len(runs[3].children) == 4
    assert any(not event["ok"] for event in runs[3].normalized()["tools"])
    assert not next(
        item for item in observed if item["step"] == 3 and item["name"] == "operation_5"
    )["ok"]
