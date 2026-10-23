import agentic_systems as toolkit


def run():
    @toolkit.tool
    def echo(value: int) -> dict:
        """Return a structured integer object."""
        return {"value": value}
    capability = toolkit.skill(name="echo", tools=[echo])
    schema = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]}
    contract = {"tool_expectation": {"all_of": ["echo"], "allowed": ["echo"], "min_count": 1},
                "failure_policy": "no_unresolved", "output_schema": schema}
    rows = []
    for name in ("native", "langgraph", "openai-agents", "strands"):
        worker = toolkit.Agent("structured_operator", runtime=toolkit.runtime(provider="python-runtime", max_turns=8, max_tool_calls=2),
            framework=toolkit.framework(name), skills=(capability,), contract=contract, policy={"trace": "compact"})
        positive = worker.run({"tool": "echo", "input": {"value": 7}})
        negative = worker.run({"tool": "echo", "input": {"value": "not-an-integer"}})
        assert positive.ok and positive.data["value"] == 7 and not negative.ok
        rows.append({"framework": name, "positive": positive.to_dict(), "negative": negative.to_dict()})
    return {"input": {"value": 7}, "process": "Required Tool + actor budget + portable JSON Schema validation",
            "output": rows, "validation": "Python Runtime; no language-model structured-output claim"}
