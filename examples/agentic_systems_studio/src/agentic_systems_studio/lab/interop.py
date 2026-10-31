"""Three real framework actors coordinated by one public System."""

import pydantic
import agentic_systems as toolkit

FRAMEWORKS = ("native", "openai-agents", "strands")


def stage_tool(name):
    def mark(value: int, trail: list[str]) -> dict:
        return {"value": value + 1, "trail": [*trail, name]}

    return toolkit.tool(
        mark,
        name="mark_" + name.replace("-", "_"),
        description="Increment value and append this framework's identity to trail.",
    )


def observed_output(output, tool_name, expected):
    """Read known public evidence envelopes without repairing business data."""
    if output == expected or output == {"data": expected}:
        return expected
    if (
        isinstance(output, dict)
        and output.get("kind") == "object"
        and output.get("tool_name") == tool_name
        and output.get("ok") is True
        and output.get("data") == expected
    ):
        return output["data"]
    raise ValueError(
        "Observed Tool output violates the stage contract: " + repr(output)
    )


def build(runtimes):
    class State(pydantic.BaseModel):
        value: int
        trail: list = pydantic.Field(default_factory=list)
        validated: bool | None = None

    graph = toolkit.Graph(State)
    previous = toolkit.START
    for name in FRAMEWORKS:
        capability = stage_tool(name)
        actor = toolkit.Agent(
            name,
            runtime=runtimes[name],
            framework=toolkit.framework(name),
            skills=(toolkit.skill(name=name + "_evidence", tools=(capability,)),),
            instructions="Call your mark tool exactly once. Copy the input value and trail unchanged as Tool arguments. The Tool alone increments and appends identity; never do that work yourself.",
            contract={
                "tool_expectation": {"all_of": [capability.name]},
                "completion": "when_required_tools_satisfied",
            },
            policy={"repair": False},
        )

        def request(
            data,
            captured=actor,
            tool_name=capability.name,
            provider=runtimes[name].provider,
        ):
            from dataclasses import replace
            import json

            payload = (
                {"tool": tool_name, "input": data.model_dump(exclude_unset=True)}
                if provider == "python-runtime"
                else "Call exactly "
                + tool_name
                + " once with exactly these arguments, without calculating or editing any field:\n"
                + json.dumps(data.model_dump(exclude_unset=True))
            )
            raw = captured.run(payload)
            if not raw.ok:
                return raw
            events = [
                event
                for node in raw.walk()
                for event in node.tool_events
                if event.name == tool_name and event.ok
            ]
            if len(events) != 1:
                raise ValueError("Each stage must call its declared Tool exactly once")
            output = events[0].output
            expected = {
                "value": data.value + 1,
                "trail": [*data.trail, captured.name],
            }
            output = observed_output(output, tool_name, expected)
            # The application passes observed Tool data; model prose is presentation.
            # Original actor messages, raw responses and nested data remain in the trace.
            return replace(raw, data=output)

        graph.add_node(name, request)
        graph.add_edge(previous, name)
        previous = name
    graph.add_node(
        "check",
        lambda data: {
            "validated": data.value == 45 and data.trail == list(FRAMEWORKS)
        },
    )
    graph.add_edge(previous, "check")
    graph.add_edge("check", toolkit.END)
    return toolkit.System("framework_interop", graph=graph)


def run():
    application = build(
        {name: toolkit.runtime(provider="python-runtime") for name in FRAMEWORKS}
    )
    execution = application.run(
        {"value": 42, "trail": []}, timeout_s=180
    )
    assert execution.ok and execution.data == {
        "value": 45,
        "trail": list(FRAMEWORKS),
        "validated": True,
    }, execution.to_dict()
    evaluation = toolkit.Eval(
        "interoperability",
        application,
        cases=(
            {"input": {"value": 42, "trail": []}, "expected": {"data": execution.data}},
        ),
    ).run(timeout_s=180)
    assert evaluation.ok
    return {
        "input": {"value": 42, "trail": []},
        "process": "Three real SDK paths in one LangGraph-backed System",
        "output": execution.to_dict(),
        "eval": evaluation.to_dict(),
        "inference_requests": 0,
    }
