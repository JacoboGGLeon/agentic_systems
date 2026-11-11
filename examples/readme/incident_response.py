"""Executable README proposal for Agentic Systems 2.1.8.

Default: local deterministic actor. Bedrock is opt-in through AS_PROVIDER.
"""
# section: application
import json
import os

import pydantic
import agentic_systems as toolkit


class Incident(pydantic.BaseModel):
    service: str
    errors: int | None = None
    action: str = "monitor"


@toolkit.tool
def inspect_service(service: str, *, context: toolkit.Context) -> dict:
    services = context.data["services"]
    if service not in services:
        raise LookupError("Unknown service")
    return {"errors": services[service]["errors"]}


context = toolkit.Context(
    {
        "services": {"catalog": {"errors": 0}, "checkout": {"errors": 7}},
        "escalation_threshold": 3,
    },
    sources=("demo-service-snapshot-v1",),
)

provider = os.getenv("AS_PROVIDER", "python-runtime")
framework = os.getenv("AS_FRAMEWORK", "native")
options = {}
if provider == "bedrock-runtime":
    import boto3

    options = {
        "model": os.environ["BEDROCK_MODEL_ID"],
        "session": boto3.Session(region_name=os.environ["AWS_REGION"]),
        "max_tokens": 256,
        "max_turns": 3,
        "max_tool_calls": 1,
        "max_retries": 0,
    }
elif provider != "python-runtime":
    raise ValueError("Choose python-runtime or bedrock-runtime")

runtime = toolkit.runtime(provider=provider, **options)
skill = toolkit.skill(name="service_inspection", tools=(inspect_service,))

inspector = toolkit.Agent(
    "inspector",
    runtime=runtime,
    framework=toolkit.framework(framework),
    skills=(skill,),
    instructions="Call inspect_service once with exactly the supplied service.",
    policy={"tool_choice": "required"},
    contract={
        "tool_expectation": {"all_of": ["inspect_service"], "min_count": 1},
        "completion": "when_required_tools_satisfied",
    },
)


def inspect_step(state):
    arguments = {"service": state.service}
    request = (
        {"tool": "inspect_service", "input": arguments}
        if provider == "python-runtime"
        else "Call inspect_service with exactly these arguments: " + json.dumps(arguments)
    )
    observed = inspector.run(request)
    if not observed.ok:
        return observed

    calls = [
        event
        for execution in observed.walk()
        for event in execution.tool_events
        if event.name == "inspect_service"
    ]
    if len(calls) != 1 or not calls[0].ok or calls[0].input != arguments:
        raise ValueError("Expected one successful inspection with exact input")
    output = calls[0].output
    data = output.get("data", output)
    if not isinstance(data, dict) or type(data.get("errors")) is not int:
        raise ValueError("Invalid inspection output")
    return {"errors": data["errors"], "action": "monitor"}


diagnostic_graph = toolkit.Graph(Incident)
diagnostic_graph.add_node("inspect", inspect_step)
diagnostic_graph.add_edge(toolkit.START, "inspect")
diagnostic_graph.add_edge("inspect", toolkit.END)
diagnostician = toolkit.Agent("diagnostician", graph=diagnostic_graph)


@toolkit.tool
def escalate(service: str, errors: int) -> dict:
    # A recorded decision; this example does not contact an external service.
    return {"action": "escalate"}


escalation_graph = toolkit.Graph(Incident)
escalation_graph.add_node("decide", escalate)
escalation_graph.add_edge(toolkit.START, "decide")
escalation_graph.add_edge("decide", toolkit.END)
escalation_agent = toolkit.Agent("escalation", graph=escalation_graph)


def route(state):
    return "escalate" if state.errors >= context.data["escalation_threshold"] else "done"


system_graph = toolkit.Graph(Incident)
system_graph.add_node("diagnose", diagnostician)
system_graph.add_node("escalate", escalation_agent)
system_graph.add_edge(toolkit.START, "diagnose")
system_graph.add_conditional_edges(
    "diagnose", route, {"escalate": "escalate", "done": toolkit.END}
)
system_graph.add_edge("escalate", toolkit.END)

system = toolkit.System("incident_response", graph=system_graph, context=context)
result = system.run({"service": "checkout"})
assert result.ok
assert result.data == {"service": "checkout", "errors": 7, "action": "escalate"}
print(result.data)
# section: evaluation


def check_inspection(result, case):
    calls = [
        event
        for execution in result.walk()
        for event in execution.tool_events
        if event.name == "inspect_service"
    ]
    escalations = [
        event
        for execution in result.walk()
        for event in execution.tool_events
        if event.name == "escalate"
    ]
    expected_escalations = int(case["input"]["service"] == "checkout")
    return {
        "ok": len(calls) == 1
        and calls[0].input == case["input"]
        and calls[0].ok == case["expected"]["ok"]
        and len(escalations) == expected_escalations
        and all(event.ok for event in escalations)
    }


evaluation = toolkit.Eval(
    "incident_acceptance",
    unit=system,
    cases=(
        {"input": {"service": "catalog"}, "expected": {"ok": True, "data": {
            "service": "catalog", "errors": 0, "action": "monitor"}}},
        {"input": {"service": "checkout"}, "expected": {"ok": True, "data": {
            "service": "checkout", "errors": 7, "action": "escalate"}}},
        {"input": {"service": "unknown"}, "expected": {"ok": False}},
    ),
    checks=(check_inspection,),
)
evaluation_result = evaluation.run()
assert evaluation_result.ok, evaluation_result.evidence()

negative_control = toolkit.Eval(
    "reject_wrong_decision",
    unit=system,
    cases=({"input": {"service": "checkout"}, "expected": {"ok": True, "data": {
        "service": "checkout", "errors": 7, "action": "monitor"}}},),
)
negative_result = negative_control.run()
assert not negative_result.ok
# section: environment

episode_graph = toolkit.Graph(Incident)
episode_graph.add_node("respond", system)
episode_graph.add_edge(toolkit.START, "respond")
episode_graph.add_edge("respond", toolkit.END)


def update(state, record, result):
    return {
        "processed": state["processed"] + 1,
        "escalations": state["escalations"] + int(result.data["action"] == "escalate"),
    }


def stop(state, result):
    return state["escalations"] >= 1


environment = toolkit.Environment(
    "service_round",
    graph=episode_graph,
    records=({"service": "catalog"}, {"service": "checkout"}, {"service": "catalog"}),
    state={"processed": 0, "escalations": 0},
    update=update,
    stop=stop,
    max_steps=3,
)
batch_result = environment.run()
assert batch_result.ok
assert len(batch_result.data["outputs"]) == 2
assert batch_result.data["summary"]["state"] == {"processed": 2, "escalations": 1}


def check_round(result, case):
    return {"ok": len(result.data["outputs"]) == 2 and
            result.data["summary"]["state"] == {"processed": 2, "escalations": 1}}


environment_eval = toolkit.Eval(
    "round_acceptance",
    unit=environment,
    cases=({"input": {}, "expected": {"ok": True}},),
    checks=(check_round,),
)
environment_eval_result = environment_eval.run()
assert environment_eval_result.ok
# section: memory


class Observation(pydantic.BaseModel):
    previous_runs: int = 0


@toolkit.tool
def recall(*, context: toolkit.Context) -> dict:
    return {"previous_runs": len(context.episodes)}


memory_graph = toolkit.Graph(Observation)
memory_graph.add_node("recall", recall)
memory_graph.add_edge(toolkit.START, "recall")
memory_graph.add_edge("recall", toolkit.END)
memory = toolkit.Memory(capacity=20)
remembering_agent = toolkit.Agent("remembering_agent", graph=memory_graph, memory=memory)
first = remembering_agent.run({})
second = remembering_agent.run({})
assert first.ok and first.data["previous_runs"] == 0
assert second.ok and second.data["previous_runs"] == 1
# section: evidence

evidence = result.evidence()
lineage = result.lineage()
assert result.check_invariants().ok
print("PASS: system, three Eval cases, negative control, Environment, Environment Eval, Memory")
