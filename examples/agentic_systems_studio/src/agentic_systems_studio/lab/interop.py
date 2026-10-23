"""Four real framework actors coordinated by one public System."""
import agentic_systems as toolkit

FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")


def stage_tool(name):
    def mark(value: int, trail: list[str]) -> dict:
        return {"value": value + 1, "trail": [*trail, name]}
    return toolkit.tool(mark, name="mark_" + name.replace("-", "_"),
                        description="Increment value and append this framework's identity to trail.")


def build(runtimes):
    actors = []
    for name in FRAMEWORKS:
        capability = stage_tool(name)
        actor = toolkit.Agent(name, runtime=runtimes[name], framework=toolkit.framework(name),
            skills=(toolkit.skill(name=name + "_evidence", tools=(capability,)),),
            instructions="Call your mark tool exactly once. Copy the input value and trail unchanged as Tool arguments. The Tool alone increments and appends identity; never do that work yourself.",
            contract={"tool_expectation": {"all_of": [capability.name]}, "completion": "when_required_tools_satisfied"},
            policy={"repair": False})
        def request(data, captured=actor, tool_name=capability.name, provider=runtimes[name].provider):
            from dataclasses import replace
            import json
            payload = ({"tool": tool_name, "input": data} if provider == "python-runtime" else
                       "Call exactly " + tool_name + " once with exactly these arguments, without calculating or editing any field:\n" + json.dumps(data))
            raw = captured.run(payload, limits=toolkit.Limits(timeout_s=180))
            if not raw.ok:
                return raw
            events = [event for node in raw.walk() for event in node.tool_events if event.name == tool_name and event.ok]
            if len(events) != 1:
                raise ValueError("Each stage must call its declared Tool exactly once")
            output = events[0].output
            expected = {"value": data["value"] + 1, "trail": [*data["trail"], captured.name]}
            if output == {"data": expected}:
                output = output["data"]
            if output != expected:
                raise ValueError("The observed Tool output violates this stage's contract: " + repr({"expected": expected, "observed": output}))
            # The application passes observed Tool data; model prose is presentation.
            # Original actor messages, raw responses and nested data remain in the trace.
            return replace(raw, data=output)
        actors.append(toolkit.Agent(name + "_stage", toolkit.Action(name + "_request", request)))
    return toolkit.System("framework_interop", toolkit.Graph(
        nodes=(("work", toolkit.Sequence(tuple(actors))),
               ("check", toolkit.Action("check", lambda data: {**data, "validated": data["value"] == 46 and data["trail"] == list(FRAMEWORKS)}))),
        edges=(("work", lambda data: "check"), ("check", "END")), start="work"), backend="langgraph")


def run():
    application = build({name: toolkit.runtime(provider="python-runtime") for name in FRAMEWORKS})
    execution = application.run({"value": 42, "trail": []}, limits=toolkit.Limits(timeout_s=180))
    assert execution.ok and execution.data == {"value": 46, "trail": list(FRAMEWORKS), "validated": True}, execution.to_dict()
    evaluation = toolkit.Eval("interoperability", application, cases=(
        {"input": {"value": 42, "trail": []}, "expected": {"data": execution.data}},
    )).run(limits=toolkit.Limits(timeout_s=180))
    assert evaluation.ok
    return {"input": {"value": 42, "trail": []}, "process": "Four real SDK paths in one LangGraph-backed System",
            "output": execution.to_dict(), "eval": evaluation.to_dict(), "inference_requests": 0}
