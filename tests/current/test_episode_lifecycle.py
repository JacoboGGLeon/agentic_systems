"""Episode controls, lazy resources and continuation ownership remain explicit."""

import asyncio
import threading

import pydantic
import pytest

import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: int


def graph(operation):
    builder = toolkit.Graph(State)
    builder.add_node("work", operation)
    builder.add_edge(toolkit.START, "work")
    builder.add_edge("work", toolkit.END)
    return builder


def keep(state):
    return {"value": state.value}


def test_episode_arun_and_invalid_stop_preserve_evidence():
    environment = toolkit.Environment("day", graph(keep), ({"value": 3},))
    result = asyncio.run(environment.arun())
    assert result.ok and result.data["outputs"] == [{"value": 3}]
    assert "records_observed" in result.human_results()
    invalid = toolkit.Environment("invalid-stop", graph(keep), ({"value": 3},), stop=lambda state, result: 1).run()
    assert not invalid.ok and "stop must return bool" in str(invalid.errors)


@pytest.mark.parametrize("options,error", [
    ({"records": ()}, ValueError),
    ({"records": [{"value": 3}]}, ValueError),
    ({"records": ({"value": 3},), "observe": 3}, TypeError),
])
def test_invalid_episode_declarations_fail_before_consumption(options, error):
    with pytest.raises(error):
        toolkit.Environment("invalid", graph(keep), **options).compile()


def test_lazy_source_close_failure_is_recorded():
    class Source:
        def __iter__(self):
            return self

        def __next__(self):
            return {"value": 3}

        def close(self):
            raise RuntimeError("source close failed")

    result = toolkit.Environment("close", graph(keep), Source, max_steps=1).run()
    assert not result.ok and "source close failed" in str(result.errors)


def test_continuation_is_owned_and_cannot_be_resumed_concurrently():
    entered, release = threading.Event(), threading.Event()

    def approve(state):
        answer = toolkit.pause({"value": state.value})
        entered.set()
        assert release.wait(3)
        return {"value": state.value + int(answer)}

    program = toolkit.Agent("approval", graph(approve)).compile()
    paused = program.run({"value": 3})
    assert paused.status == "paused"
    with pytest.raises(ValueError, match="paused RunResult"):
        program.resume(toolkit.RunResult(), True)
    results = []
    worker = threading.Thread(target=lambda: results.append(program.resume(paused, True)))
    worker.start()
    assert entered.wait(2)
    try:
        with pytest.raises(ValueError, match="already running"):
            program.resume(paused, True)
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive() and results[0].ok and results[0].data == {"value": 4}


def test_expired_root_deadline_prevents_business_effects():
    calls = []

    def operation(state):
        calls.append(state.value)
        return {"value": state.value}

    result = toolkit.Agent("expired", graph(operation)).run({"value": 3}, timeout_s=1e-12)
    assert not result.ok and not calls


def test_prepared_nested_runs_share_root_deadline():
    prepared = toolkit.Agent("child", graph(keep)).compile()

    def parent(state):
        result = prepared.run({"value": state.value})
        assert result.ok
        return result.data

    result = toolkit.System("parent", graph(parent)).run({"value": 3})
    assert result.ok and result.data == {"value": 3}

    def invalid(state):
        return prepared.run({"value": state.value}, timeout_s=2).data

    result = toolkit.System("invalid", graph(invalid)).run({"value": 3})
    assert not result.ok and "root deadline" in str(result.errors)
