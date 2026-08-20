from __future__ import annotations

import random

import pytest
from pydantic import ValidationError

from agentic_systems import AgenticEnvironment, EvalReport, run_eval
from agentic_systems.evals import EvalReproducibility
from agentic_systems.results import RunResult


class _DeterministicAgent:
    def run(self, input_value, mode="eval", config=None):
        return RunResult(text=str(input_value), data={"value": input_value}, ok=True, mode=mode)


def _run_episode(env: AgenticEnvironment, seed: int) -> tuple[list[float], dict]:
    observation, info = env.reset(seed=seed)
    assert observation is not None
    while observation is not None:
        observation, _reward, terminated, truncated, info = env.step()
        if terminated or truncated:
            break
    return [event.graph_state["sample"] for event in env.history], info


def test_environment_seed_owns_a_local_replayable_rng_and_evidence():
    env = None

    def transition(row, action, info):
        assert env is not None
        return {"sample": env.rng.random(), "seed_seen": info["episode"]["seed"]}

    env = AgenticEnvironment(records=[{"id": 1}, {"id": 2}], transition_fn=transition)
    first, first_info = _run_episode(env, 17)
    second, second_info = _run_episode(env, 17)

    assert first == second
    assert env.seed == 17
    assert first_info["seed"] == second_info["seed"] == 17
    assert env.summary()["seed"] == 17
    assert all(event.graph_state["seed_seen"] == 17 for event in env.history)


def test_environment_seed_does_not_mutate_the_process_random_generator():
    state = random.getstate()
    try:
        random.seed(23)
        expected = random.random()
        random.seed(23)
        env = AgenticEnvironment(records=[], transition_fn=lambda row, action, info: {})
        env.reset(seed=99)
        assert random.random() == expected
    finally:
        random.setstate(state)


def test_eval_reports_classification_seed_conditions_and_consistent_serialization():
    cases = [{"name": "one", "input": "same", "expected": {"text_contains": "same"}}]
    first = run_eval(
        _DeterministicAgent(),
        cases,
        determinism="deterministic",
        seed=41,
        reproducibility_conditions=["same fixture snapshot"],
    )
    second = run_eval(_DeterministicAgent(), cases, determinism="deterministic", seed=41)

    assert first.cases == second.cases
    assert first.reproducibility.classification == "deterministic"
    assert first.reproducibility.seed == 41
    assert first.reproducibility.replayable is True
    assert "same fixture snapshot" in first.reproducibility.conditions
    assert first.to_dict()["reproducibility"] == first.normalized()["input"]["reproducibility"]

    default_report = run_eval(_DeterministicAgent(), cases)
    assert default_report.reproducibility.classification == "non_deterministic"
    assert default_report.reproducibility.replayable is False

    seeded_report = run_eval(_DeterministicAgent(), cases, determinism="seeded", seed=41)
    assert seeded_report.reproducibility.classification == "seeded"
    assert any("consume the declared seed" in item for item in seeded_report.reproducibility.conditions)


def test_eval_reproducibility_and_report_aggregates_reject_contradictions():
    with pytest.raises(ValidationError, match="requires a non-null seed"):
        EvalReproducibility(classification="seeded", seed=None, replayable=True)
    with pytest.raises(ValidationError, match="cannot promise replayable=True"):
        EvalReproducibility(classification="non_deterministic", replayable=True)

    with pytest.raises(ValidationError, match="EvalReport aggregates are inconsistent"):
        EvalReport(ok=False, total=1, passed=1, failed=1, pass_rate=0.0, cases=[])
