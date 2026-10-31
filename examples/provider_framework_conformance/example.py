import agentic_systems as toolkit


def run():

    @toolkit.tool
    def echo(value: int) -> dict:
        """Return the supplied integer."""
        return {"value": value}

    capability = toolkit.skill(
        name="echo", tools=[echo], instructions="Return the exact Tool result."
    )
    rows = []
    for name in ("native", "openai-agents", "strands"):
        actor = toolkit.Agent(
            "operator",
            runtime=toolkit.runtime(
                provider="python-runtime", timeout_s=60, max_turns=8, max_tool_calls=2
            ),
            framework=toolkit.framework(name),
            skills=(capability,),
        )
        result = actor.run(
            {"tool": "echo", "input": {"value": 3}}, timeout_s=60
        )
        assert result.ok and result.data["value"] == 3, {
            "framework": name,
            "result": result.to_dict(),
        }
        rows.append({"framework": name, "output": result.to_dict()})
    external = {
        name: toolkit.runtime(provider=name, model="explicit-configured-only").inspect()
        for name in (
            "openai-runtime",
            "ollama-runtime",
            "bedrock-runtime",
            "vllm-runtime",
        )
    }
    return {
        "input": {"tool": "echo", "input": {"value": 3}},
        "process": "Four framework Python operators; external provider configuration only",
        "output": rows,
        "external": external,
        "external_validation": "configured-only; not run",
    }
