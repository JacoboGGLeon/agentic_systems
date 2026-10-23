import agentic_systems as toolkit


def run():
    artifact = toolkit.model_artifact("fixture/model", base_model="fixture/base", tokenizer="fixture/tokenizer",
        adapter_path="adapter", revision="fixture-revision", quantization="int8", metadata={"synthetic": True})
    server = toolkit.model_server(artifact, profile="custom", served_model_name="fixture", host="127.0.0.1", port=8123,
        tool_call_parser="hermes", reasoning_parser="fixture-parser", enable_auto_tool_choice=True,
        startup_timeout_s=10.0, log_path="fixture-vllm.log", binary="vllm", extra_args=("--dtype", "auto"),
        gpu_memory_utilization=0.5, max_model_len=1024, max_num_seqs=2)
    config = toolkit.runtime(provider="vllm-runtime", endpoint=server.endpoint.url, model=server.endpoint.model)
    return {"input": artifact.inspect(), "process": "Declare and inspect; no start, health request, model download or inference",
            "output": server.inspect(), "runtime": config.inspect(), "validation": "configured-only; lifecycle tested separately with fakes"}
