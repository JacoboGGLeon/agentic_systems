import agentic_systems as toolkit


def run():
    artifact = toolkit.model_artifact(
        "Qwen/Qwen3-0.6B",
        revision="main",
        metadata={"scope": "declaration only; GPU not validated"},
    )
    server = toolkit.model_server(
        artifact,
        profile="custom",
        served_model_name="Qwen/Qwen3-0.6B",
        gpu_memory_utilization=0.75,
        max_model_len=2048,
        max_num_seqs=1,
        enable_auto_tool_choice=False,
        tool_call_parser=None,
    )
    config = toolkit.runtime(
        provider="vllm-runtime",
        endpoint=server.endpoint.url,
        model=server.endpoint.model,
    )
    return {
        "input": artifact.inspect(),
        "process": "Declare and inspect; no start, download or inference",
        "output": server.inspect(),
        "runtime": config.inspect(),
        "validation": "configuration-only; GPU pending",
    }
