"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def echo(value: int) -> dict:
    return {"value": value}


def run():
    rows = []
    for framework in ("native", "langgraph", "openai-agents", "strands"):
        worker = toolkit.Agent("operator", runtime=toolkit.runtime(provider="python-runtime"), framework=toolkit.framework(framework),
            skills=(toolkit.skill(name="echo", tools=(echo,)),))
        result = worker.run({"tool": "echo", "input": {"value": 3}})
        assert result.ok
        rows.append({"framework": framework, "result": result.to_dict()})
    return {"scope": "real SDKs with deterministic Python; live evidence is separate", "rows": rows}
