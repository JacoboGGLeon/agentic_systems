"""Private implementation of canonical runtime and resource configuration."""
from .core.runtime import RuntimeConfig
from .core.scheduler import SchedulerConfig
from .integrations.config import FrameworkConfig
from ._factories import model_artifact as _model_artifact, model_server as _model_server
from .schemas.serving import ModelArtifact as _ModelArtifact

_PROVIDERS = {"python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"}


def runtime(*, provider, model=None, region=None, endpoint=None, api_key=None,
            timeout_s=60.0, max_retries=0, max_tool_calls=5, max_turns=6):
    if provider not in _PROVIDERS:
        raise ValueError("Choose an explicit provider: " + ", ".join(sorted(_PROVIDERS)))
    return RuntimeConfig(
        provider=provider, model_id=model or ("python-runtime" if provider == "python-runtime" else None),
        region_name=region, endpoint=endpoint, api_key=api_key,
        scheduler=SchedulerConfig(timeout_s=timeout_s, max_retries=max_retries,
                                  max_tool_calls=max_tool_calls, max_turns=max_turns),
    )


def framework(name, *, agent_kwargs=None, run_kwargs=None):
    return FrameworkConfig(name=name, agent_kwargs=agent_kwargs or {}, run_kwargs=run_kwargs or {})


def model_artifact(model, *, base_model=None, adapter_path=None, tokenizer=None,
                   revision=None, quantization=None, metadata=None):
    return _model_artifact(model, base_model=base_model, adapter_path=adapter_path,
                           tokenizer=tokenizer, revision=revision,
                           quantization=quantization, metadata=metadata)


def model_server(artifact, **configuration):
    if not isinstance(artifact, _ModelArtifact):
        raise TypeError("Pass the artifact returned by model_artifact(...)")
    if {"spec", "model", "backend"}.intersection(configuration):
        raise TypeError("model_server accepts one artifact and its serving configuration")
    return _model_server(artifact, **configuration)
