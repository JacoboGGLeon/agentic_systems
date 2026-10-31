"""Runtime and scheduler remain execution pillars, without another constructor."""

import pydantic
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: int


@toolkit.tool
def echo(value: int) -> dict:
    return {"value": value}


def run():
    execution = toolkit.runtime(
        provider="python-runtime",
        timeout_s=30,
        max_turns=2,
        max_tool_calls=1,
        max_retries=0,
        backoff_s=0,
        max_concurrency=1,
    )
    adapter = toolkit.framework("native")
    actor = toolkit.Agent(
        "bounded_operator",
        runtime=execution,
        framework=adapter,
        skills=(toolkit.skill(name="echo", tools=(echo,)),),
        policy={"repair": False, "trace": "compact"},
        contract={
            "tool_expectation": {"all_of": ["echo"]},
            "output_schema": State.model_json_schema(),
        },
    )
    graph = toolkit.Graph(State)
    graph.add_node("echo", actor)
    graph.add_edge(toolkit.START, "echo")
    graph.add_edge("echo", toolkit.END)
    system = toolkit.System("bounded_system", graph=graph)
    deadline_s = 60
    result = system.run(State(value=3), timeout_s=deadline_s)
    assert result.ok and result.data == {"value": 3}, result.to_dict()
    negative = system.run({"value": "invalid"}, timeout_s=deadline_s)
    assert not negative.ok
    assert isinstance(execution, pydantic.BaseModel)
    assert isinstance(adapter, pydantic.BaseModel)
    for bad in (
        {"max_retries": -1},
        {"max_concurrency": 0},
        {"timeout_s": float("inf")},
    ):
        try:
            toolkit.runtime(provider="python-runtime", **bad)
        except pydantic.ValidationError:
            pass
        else:
            raise AssertionError("Invalid controls must fail before effects")
    return {
        "input": {"value": 3},
        "process": "runtime + scheduler caps -> actor -> root deadline",
        "output": result.to_dict(),
        "negative": negative.to_dict(),
        "runtime": execution.inspect(),
        "timeout_s": deadline_s,
        "inference_requests": 0,
    }
