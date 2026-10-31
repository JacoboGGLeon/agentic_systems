"""Local Skill loading and declarative model serving; safe to run offline."""

import pydantic
from pathlib import Path
import agentic_systems as toolkit


class QuoteState(pydantic.BaseModel):
    subtotal: int
    total: int | None = None
    currency: str | None = None
    policy_source: str | None = None
    previous_episodes: int | None = None
    preceding_events: int | None = None


def loaded_skill_example():
    capability = toolkit.load_skill(Path(__file__).parent / "skills/pricing")
    graph = toolkit.Graph(QuoteState)
    graph.add_node("quote", capability.tools[0])
    graph.add_edge(toolkit.START, "quote")
    graph.add_edge("quote", toolkit.END)
    agent = toolkit.Agent(
        "quote",
        graph=graph,
        skills=(capability,),
        context=toolkit.Context(
            {"currency": "MXN", "tax_percent": 16}, sources=("tax-policy-v1",)
        ),
        memory=toolkit.Memory(),
    )
    first = agent.run({"subtotal": 100})
    second = agent.run({"subtotal": 100})
    assert (
        first.ok
        and first.data["total"] == 116
        and (first.data["previous_episodes"] == 0)
    )
    assert second.ok and second.data["previous_episodes"] == 1
    return {
        "input": {"subtotal": 100},
        "process": "load_skill → quote with Context → remember",
        "output": first.data,
        "skill": capability.inspect(),
        "run_results": [first.to_dict(), second.to_dict()],
    }


def serving_example():
    artifact = toolkit.model_artifact(
        "Qwen/Qwen2.5-0.5B-Instruct",
        revision="main",
        metadata={
            "purpose": "offline serving declaration; weights not downloaded or validated"
        },
    )
    server = toolkit.model_server(
        artifact,
        profile="custom",
        served_model_name="quote-model",
        gpu_memory_utilization=0.5,
        max_model_len=2048,
        max_num_seqs=1,
        enable_auto_tool_choice=False,
        tool_call_parser=None,
        api_key="example-local-token",
    )
    runtime = toolkit.runtime(
        provider="vllm-runtime",
        model=server.endpoint.model,
        endpoint=server.endpoint.url,
        api_key="example-local-token",
        max_tokens=128,
    )
    description = server.inspect()
    assert description["endpoint"]["model"] == "quote-model"
    assert server.endpoint.owned is False and "example-local-token" not in str(
        description
    )
    assert "--max-model-len" in server.command and "2048" in server.command
    return {
        "artifact": artifact.inspect(),
        "server": description,
        "runtime": runtime.inspect(),
        "validation": "declaration, command, endpoint, redaction; no GPU, health probe, process start or inference",
    }
