"""Shared real framework probes; the caller owns authorization and budget."""
import json
import agentic_systems as toolkit
from ..routes import make_runtime, values

FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")

@toolkit.tool
def certify(value: int) -> dict:
    """Return exact deterministic evidence for the requested integer."""
    return {"value": value, "verified": True}


def matrix(provider, framework):
    runtime = make_runtime(provider, max_tokens=256)
    actor = toolkit.Agent("matrix", runtime=runtime, framework=toolkit.framework(framework),
        skills=(toolkit.skill(name="evidence", tools=(certify,)),),
        instructions="Call certify once with the requested integer.",
        contract={"tool_expectation": {"all_of": ["certify"]}, "completion": "when_required_tools_satisfied"},
        policy={"repair": False})
    value = 37
    result = actor.run({"tool": "certify", "input": {"value": value}} if provider == "python-runtime" else
                       "Call certify with value=37. The tool output is the required result.", limits=toolkit.Limits(timeout_s=180))
    events = [event for node in result.walk() for event in node.tool_events]
    assert result.ok and any(e.name == "certify" and e.ok and e.input.get("value") == value for e in events), result.to_dict()
    assert result.check_invariants().ok
    assert json.loads(json.dumps(result.to_dict()))["ok"]
    return {"provider": provider, "framework": framework, "result": result.to_dict()}


def handoffs(provider):
    from .native_profiles import handoff_destination
    from agents import GuardrailFunctionOutput, input_guardrail, SQLiteSession
    observed = []
    native_handoff = handoff_destination(provider, values(provider), observed)

    @input_guardrail(run_in_parallel=False)
    def block(context, agent, request):
        return GuardrailFunctionOutput(output_info={"checked": True}, tripwire_triggered="BLOCKED_REQUEST" in str(request))

    session = SQLiteSession("handoff-213-" + provider, ":memory:")
    try:
        actor = toolkit.Agent("triage", runtime=make_runtime(provider, max_tokens=256),
            framework=toolkit.framework("openai-agents", agent_kwargs={"handoffs": [native_handoff], "input_guardrails": [block]},
                                        run_kwargs={"session": session}),
            instructions="Always transfer control to billing_specialist. Never answer the request yourself.")
        request = {"tool": native_handoff.tool_name, "input": {}} if provider == "python-runtime" else "Transfer this billing question to billing_specialist now."
        result = actor.run(request, limits=toolkit.Limits(timeout_s=180))
        negative = actor.run("BLOCKED_REQUEST", limits=toolkit.Limits(timeout_s=30))
        assert result.ok and "SPECIALIST_OK" in result.text and observed
        assert not negative.ok
        assert any(event.meta.get("kind") == "handoff" for node in result.walk() for event in node.tool_events)
        return {"provider": provider, "framework": "openai-agents", "handoff_callback": observed,
                "result": result.to_dict(), "guardrail_negative": negative.to_dict()}
    finally:
        session.close()


def protocols(provider, kind, budget):
    from .protocols import strands_tools
    with strands_tools(kind, budget) as (tools, witness):
        name = "echo" if kind == "mcp" else "call_remote_echo"
        actor = toolkit.Agent("strands_protocol", runtime=make_runtime(provider, max_tokens=256),
            framework=toolkit.framework("strands", agent_kwargs={"tools": tools}),
            instructions="Call " + name + " once with value=FRAMEWORKS_TOGETHER. Return the exact tool evidence.", policy={"repair": False})
        result = actor.run({"tool": name, "input": {"value": "FRAMEWORKS_TOGETHER"}} if provider == "python-runtime" else
                          "Call " + name + " with value=FRAMEWORKS_TOGETHER.", limits=toolkit.Limits(timeout_s=180))
        assert result.ok, result.to_dict()
        assert any(event.name == name and event.ok and "FRAMEWORKS_TOGETHER" in json.dumps(event.output)
                   for node in result.walk() for event in node.tool_events), result.to_dict()
        return {"provider": provider, "framework": "strands", "protocol": witness, "result": result.to_dict()}


def interop(mixed):
    from .interop import build, FRAMEWORKS
    selected = dict(zip(FRAMEWORKS, ("python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime"))) if mixed else dict.fromkeys(FRAMEWORKS, "python-runtime")
    app = build({name: make_runtime(provider, max_tokens=256) for name, provider in selected.items()})
    result = app.run({"value": 42, "trail": []}, limits=toolkit.Limits(timeout_s=240))
    assert result.ok and result.data == {"value": 46, "trail": list(FRAMEWORKS), "validated": True}, result.to_dict()
    return {"assignments": selected, "result": result.to_dict()}


