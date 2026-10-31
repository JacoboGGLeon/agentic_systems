"""Episode bounds, source lifecycle and reference integrity."""
from dataclasses import replace
import json

import pytest
import agentic_systems as toolkit


def worker(backend="native"):
    return toolkit.Agent("echo", toolkit.Sequence((toolkit.Action("echo", lambda d: d),)), backend=backend)


@pytest.mark.parametrize("limit", [0, -1, "inf", float("inf"), True, 1.5])
def test_one_spelling_for_unbounded_steps(limit):
    with pytest.raises((ValueError, TypeError)):
        toolkit.Environment("episode", worker(), ({"value": 1},), max_steps=limit).compile()


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("limit,processed,reason", [(None, 3, "records_exhausted"), (1, 1, "step_limit"), (3, 3, "records_exhausted"), (5, 3, "records_exhausted")])
def test_positive_steps_are_a_ceiling_never_padding_or_execution_failure(backend, limit, processed, reason):
    result = toolkit.Environment("episode", worker(backend), tuple({"value": i} for i in range(3)), max_steps=limit).run()
    assert result.ok and result.data["summary"]["processed"] == processed
    assert result.data["summary"]["reason"] == reason
    assert result.data["summary"]["truncated"] == (reason == "step_limit")
    assert result.check_invariants().ok


def test_terminal_condition_may_stop_before_maximum():
    result = toolkit.Environment("episode", worker(), tuple({"value": i} for i in range(10)), max_steps=8,
                                 stop=lambda state, result: result.data["value"] == 1).run()
    assert result.ok and result.data["summary"]["processed"] == 2
    assert result.data["summary"]["terminated"] and result.data["summary"]["reason"] == "stop"


def test_unbounded_lazy_source_stops_and_is_not_started_during_compile():
    seen, closed = [], []
    def source():
        try:
            value = 0
            while True:
                seen.append(value)
                yield {"value": value}
                value += 1
        finally:
            closed.append(True)
    episode = toolkit.Environment("stream", worker(), source, stop=lambda state, result: result.data["value"] == 2)
    prepared = episode.compile()
    assert prepared.inspect()["records"] == "lazy" and not seen
    first = prepared.run()
    assert first.ok and first.data["summary"]["processed"] == 3
    assert seen == [0, 1, 2] and closed == [True]
    assert prepared.run().ok and len(closed) == 2


def test_step_limit_does_not_consume_an_extra_observation_and_closes_source():
    seen, closed = [], []
    def source():
        try:
            for i in range(10):
                seen.append(i)
                yield {"value": i}
        finally:
            closed.append(True)
    result = toolkit.Environment("stream", worker(), source, max_steps=2).run()
    assert result.ok and result.data["summary"]["truncated"]
    assert seen == [0, 1] and closed == [True]


def test_no_step_ceiling_still_obeys_shared_execution_limits():
    def source():
        while True:
            yield {"value": 1}
    result = toolkit.Environment("stream", worker(), source).run(limits=toolkit.Limits(max_actions=3))
    assert not result.ok and result.meta["actions_observed"] == 3
    assert result.data["summary"]["reason"] == "execution_limit"
    assert result.data["summary"]["truncated"]


def test_history_references_each_result_exactly_once():
    count = 100
    result = toolkit.Environment("long", worker(), tuple({"value": i} for i in range(count))).run(limits=toolkit.Limits(max_actions=count + 1))
    assert result.ok and len(result.data["history"]) == count
    assert all(row["execution_id"] == child.execution_id for row, child in zip(result.data["history"], result.children))
    encoded_history = json.dumps(result.data["history"])
    assert '"children"' not in encoded_history and '"graph_state"' not in encoded_history
    assert result.check_invariants().ok


def test_source_failure_is_not_reported_as_normal_termination():
    def source():
        yield {"value": 1}
        raise RuntimeError("controlled source failure")
    result = toolkit.Environment("stream", worker(), source).run()
    assert not result.ok and result.data["summary"]["reason"] == "execution_failed"
    assert not result.data["summary"]["terminated"] and not result.data["summary"]["truncated"]
    assert result.children[0].ok


def test_eval_preserves_environment_state_and_distinguishes_domain_result():
    episode = toolkit.Environment("episode", worker(), ({"value": 1},), state={"total": 0},
                                  update=lambda state, row, result: {"total": state["total"] + result.data["value"]})
    evaluation = toolkit.Eval("state-contract", episode, ({"input": {"state": {"total": 10}}, "expected": {"ok": True}},),
                              checks=(lambda result, case: {"ok": result.data["summary"]["state"] == {"total": 11}},))
    assert evaluation.run().ok
    assert replace(episode, state={"total": 0}).run().data["summary"]["state"] == {"total": 1}


def test_source_closes_on_keyboard_interrupt_without_swallowing_it():
    closed = []
    def source():
        try:
            yield {"value": 1}
            raise KeyboardInterrupt()
        finally:
            closed.append(True)
    with pytest.raises(KeyboardInterrupt):
        toolkit.Environment("stream", worker(), source).run()
    assert closed == [True]


def test_close_failure_is_not_silent_success():
    class Source:
        def __iter__(self):
            return self
        def __next__(self):
            return {"value": 1}
        def close(self):
            raise ValueError("controlled close failure")
    result = toolkit.Environment("stream", worker(), Source, max_steps=1).run()
    assert not result.ok and result.data["summary"]["reason"] == "source_close_failed"
    assert "controlled close failure" in str(result.errors)
