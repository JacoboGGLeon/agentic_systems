"""One spelling and one immutable configuration per execution responsibility."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from types import MappingProxyType

from ._results import _json, _redact

_PROVIDERS = {"python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"}
_FRAMEWORKS = {"native", "langgraph", "openai-agents", "strands"}


@dataclass(frozen=True)
class _Runtime:
    provider: str
    model: str | None
    region: str | None
    endpoint: str | None
    _api_key: str | None = field(repr=False)
    timeout_s: float
    max_retries: int
    max_tool_calls: int
    max_turns: int
    max_tokens: int | None
    backoff_s: float
    max_concurrency: int

    def inspect(self):
        return {"provider": self.provider, "model": self.model, "region": self.region, "endpoint": self.endpoint,
                "api_key_configured": self._api_key is not None, "timeout_s": self.timeout_s,
                "max_retries": self.max_retries, "max_tool_calls": self.max_tool_calls,
                "max_turns": self.max_turns, "max_tokens": self.max_tokens,
                "backoff_s": self.backoff_s, "max_concurrency": self.max_concurrency}

    def _to_engine(self):
        from ._engine.core.runtime import RuntimeConfig
        from ._engine.core.scheduler import SchedulerConfig
        return RuntimeConfig(provider=self.provider, model_id=self.model, region_name=self.region,
                             endpoint=self.endpoint, api_key=self._api_key,
                             scheduler=SchedulerConfig(timeout_s=self.timeout_s, max_retries=self.max_retries,
                                 max_tool_calls=self.max_tool_calls, max_turns=self.max_turns,
                                 max_concurrency=self.max_concurrency, backoff_s=self.backoff_s))


def runtime(*, provider, model=None, region=None, endpoint=None, api_key=None, timeout_s=60.0,
            max_retries=0, max_tool_calls=5, max_turns=6, max_tokens=None, backoff_s=0.0, max_concurrency=1):
    if provider not in _PROVIDERS:
        raise ValueError("Choose an explicit provider: " + ", ".join(sorted(_PROVIDERS)))
    for name, value, minimum in (("max_retries", max_retries, 0), ("max_tool_calls", max_tool_calls, 0),
                                  ("max_turns", max_turns, 1), ("max_concurrency", max_concurrency, 1)):
        if type(value) is not int or value < minimum:
            raise ValueError(name + " is outside its supported range")
    if max_tokens is not None and (type(max_tokens) is not int or max_tokens < 1):
        raise ValueError("max_tokens must be positive")
    if type(timeout_s) not in {int, float} or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be positive and finite")
    if type(backoff_s) not in {int, float} or not math.isfinite(backoff_s) or backoff_s < 0:
        raise ValueError("backoff_s must be nonnegative and finite")
    for name, value in (("model", model), ("region", region), ("endpoint", endpoint), ("api_key", api_key)):
        if value is not None and (not isinstance(value, str) or not value):
            raise TypeError(name + " must be a nonempty string")
    if region is not None and provider != "bedrock-runtime":
        raise ValueError("region belongs to Bedrock")
    if provider == "python-runtime" and any(v is not None for v in (region, endpoint, api_key, max_tokens)):
        raise ValueError("Python Runtime does not consume model connection/generation options")
    return _Runtime(provider, model or ("python-runtime" if provider == "python-runtime" else None), region,
                    endpoint, api_key, timeout_s, max_retries, max_tool_calls, max_turns, max_tokens, backoff_s, max_concurrency)


@dataclass(frozen=True)
class _Framework:
    name: str
    agent_kwargs: object
    run_kwargs: object

    def inspect(self):
        return {"name": self.name, "agent_kwargs": {k: type(v).__name__ for k, v in self.agent_kwargs.items()},
                "run_kwargs": {k: type(v).__name__ for k, v in self.run_kwargs.items()}}

    def _to_engine(self):
        from ._engine.integrations.config import FrameworkConfig
        return FrameworkConfig(name=self.name, agent_kwargs=dict(self.agent_kwargs), run_kwargs=dict(self.run_kwargs))


def framework(name, *, agent_kwargs=None, run_kwargs=None):
    if name not in _FRAMEWORKS:
        raise ValueError("Choose an exact framework name: " + ", ".join(sorted(_FRAMEWORKS)))
    if agent_kwargs is not None and not isinstance(agent_kwargs, dict) or run_kwargs is not None and not isinstance(run_kwargs, dict):
        raise TypeError("Framework options must be dictionaries")
    if name in {"native", "langgraph"} and (agent_kwargs or run_kwargs):
        raise ValueError("This adapter does not forward native SDK options")
    from ._engine.integrations.config import RESERVED_AGENT_KWARGS, RESERVED_RUN_KWARGS
    owned = {"runtime", "model", "provider", "api_key", "endpoint", "timeout_s", "max_retries", "max_tokens", "max_turns", "max_tool_calls", "contract", "policy", "limits"}
    if (set(agent_kwargs or {}) & (set(RESERVED_AGENT_KWARGS) | owned)
            or set(run_kwargs or {}) & (set(RESERVED_RUN_KWARGS) | owned)):
        raise ValueError("Framework options cannot override toolkit-owned configuration")
    def nested_conflict(value):
        if isinstance(value, dict):
            return bool(set(value) & owned) or any(nested_conflict(v) for v in value.values())
        return False
    for options in (agent_kwargs or {}, run_kwargs or {}):
        for key, value in options.items():
            if key in {"model_settings", "model_kwargs", "generation_config", "run_config", "config"}:
                settings = value if isinstance(value, dict) else vars(value) if hasattr(value, "__dict__") else {}
                settings = {k: v for k, v in settings.items() if v is not None}
                if nested_conflict(settings):
                    raise ValueError("Nested SDK options cannot override toolkit-owned configuration")
    return _Framework(name, MappingProxyType(dict(agent_kwargs or {})), MappingProxyType(dict(run_kwargs or {})))


@dataclass(frozen=True)
class _Artifact:
    model: str
    base_model: str | None
    adapter_path: str | None
    tokenizer: str | None
    revision: str | None
    quantization: str | None
    metadata: object

    def inspect(self):
        return {"model": self.model, "base_model": self.base_model, "adapter_path": self.adapter_path,
                "tokenizer": self.tokenizer, "revision": self.revision, "quantization": self.quantization,
                "metadata": _json(dict(self.metadata))}

    def _to_engine(self):
        from ._engine.schemas.serving import ModelArtifact
        return ModelArtifact(model_id=self.model, base_model_id=self.base_model, adapter_path=self.adapter_path,
                             tokenizer_id=self.tokenizer, revision=self.revision, quantization=self.quantization, metadata=dict(self.metadata))


def model_artifact(model, *, base_model=None, adapter_path=None, tokenizer=None, revision=None, quantization=None, metadata=None):
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model identity is required")
    result = _Artifact(model, base_model, adapter_path, tokenizer, revision, quantization, MappingProxyType(_json(metadata or {})))
    result._to_engine()
    return result


@dataclass(frozen=True)
class _Endpoint:
    url: str
    model: str
    backend: str
    api_key_configured: bool
    pid: int | None
    owned: bool


@dataclass(frozen=True)
class _Health:
    status: str
    endpoint: _Endpoint
    detail: str | None


def _endpoint(value):
    return _Endpoint(value.base_url, value.model_id, value.backend, value.api_key_configured, value.pid, value.owned)


@dataclass(frozen=True)
class _Server:
    _resource: object = field(repr=False)

    @property
    def endpoint(self):
        return _endpoint(self._resource.endpoint)

    @property
    def command(self):
        key = self._resource.spec.api_key.get_secret_value()
        args = self._resource.command
        return tuple("[REDACTED]" if i and args[i-1] == "--api-key" else v.replace(key, "[REDACTED]")
                     if key and key != "vllm" else v for i, v in enumerate(args))

    def inspect(self):
        value = self._resource.inspect()
        value["command"] = list(self.command)
        value["endpoint"] = self.endpoint.__dict__.copy()
        configuration = value.pop("spec")
        artifact = configuration["artifact"]
        for before, after in (("model_id", "model"), ("base_model_id", "base_model"), ("tokenizer_id", "tokenizer")):
            artifact[after] = artifact.pop(before)
        value["configuration"] = configuration
        return _redact(value)

    def start(self):
        return _endpoint(self._resource.start())

    def health(self):
        value = self._resource.health()
        key = self._resource.spec.api_key.get_secret_value()
        return _Health(value.status, _endpoint(value.endpoint), value.detail.replace(key, "[REDACTED]") if key and value.detail else value.detail)

    def stop(self):
        self._resource.stop()


def model_server(artifact, *, profile="fast", served_model_name=None, host="127.0.0.1", port=8000,
                 tool_call_parser="hermes", reasoning_parser=None, enable_auto_tool_choice=True,
                 api_key="vllm", startup_timeout_s=600.0, log_path="vllm-server.log", binary="vllm", extra_args=(),
                 gpu_memory_utilization=None, max_model_len=None, max_num_seqs=None):
    if not isinstance(artifact, _Artifact):
        raise TypeError("Pass model_artifact(...)")
    managed = {"--host", "--port", "--served-model-name", "--gpu-memory-utilization", "--max-model-len", "--max-num-seqs",
               "--tool-call-parser", "--reasoning-parser", "--enable-auto-tool-choice", "--api-key", "--generation-config"}
    if not isinstance(extra_args, tuple) or any(not isinstance(v, str) or v.split("=", 1)[0] in managed for v in extra_args):
        raise ValueError("extra_args cannot override managed server parameters")
    if profile not in {"fast", "medium", "power", "custom"}:
        raise ValueError("Unknown exact server profile")
    from ._engine.serving.vllm import VLLMServer, vllm_server_spec
    spec = vllm_server_spec(artifact._to_engine(), profile=profile, served_model_name=served_model_name, host=host, port=port,
            tool_call_parser=tool_call_parser, reasoning_parser=reasoning_parser, enable_auto_tool_choice=enable_auto_tool_choice,
            api_key=api_key, startup_timeout_s=startup_timeout_s, log_path=log_path, binary=binary, extra_args=extra_args,
            gpu_memory_utilization=gpu_memory_utilization, max_model_len=max_model_len, max_num_seqs=max_num_seqs)
    return _Server(VLLMServer(spec))
