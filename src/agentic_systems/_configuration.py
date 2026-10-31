"""One spelling and one immutable configuration per execution responsibility."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from types import MappingProxyType
from typing import Annotated, Any, Literal, Mapping
from pydantic import ConfigDict, Field, PrivateAttr, SecretStr, StrictFloat, StrictInt, StrictStr, field_serializer, field_validator, model_validator
from ._engine.schemas.execution import SchedulerSettings
from ._engine.schemas.base import ContractModel

from ._results import _json, _redact

_PROVIDERS = {"python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"}
_FRAMEWORKS = {"native", "openai-agents", "strands"}


_Text = Annotated[StrictStr, Field(min_length=1)]


class _Runtime(SchedulerSettings):
    _session_pid: int = PrivateAttr(default_factory=os.getpid)
    provider: Literal["python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"]
    model: _Text | None = None
    region: _Text | None = None
    endpoint: _Text | None = None
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    session: Any = Field(default=None, exclude=True, repr=False)
    timeout_s: StrictFloat | StrictInt = Field(default=60.0, gt=0)
    max_turns: StrictInt = Field(default=6, ge=1)
    max_tool_calls: StrictInt = Field(default=5, ge=0)
    max_tokens: StrictInt | None = Field(default=None, ge=1)

    @field_validator("api_key")
    @classmethod
    def nonempty_secret(cls, value):
        if value is not None and not value.get_secret_value():
            raise ValueError("api_key must be nonempty")
        return value

    @model_validator(mode="after")
    def provider_options(self):
        from ._session import validate_session
        validate_session(self.session, self.provider, self.region, self.api_key, self.endpoint)
        if self.session is not None and self.region is None:
            object.__setattr__(self, "region", getattr(self.session, "region_name", None))
        if self.region is not None and self.provider != "bedrock-runtime":
            raise ValueError("region belongs to Bedrock")
        if self.provider == "python-runtime":
            if any(value is not None for value in (self.region, self.endpoint, self.api_key, self.max_tokens)):
                raise ValueError("Python Runtime does not consume model connection/generation options")
            if self.model is None:
                object.__setattr__(self, "model", "python-runtime")
        return self

    @property
    def _api_key(self):
        return None if self.api_key is None else self.api_key.get_secret_value()

    def inspect(self):
        return {"provider": self.provider, "model": self.model, "region": self.region, "endpoint": self.endpoint,
                "api_key_configured": self._api_key is not None, "session_configured": self.session is not None,
                "authentication_mode": "aws-session-iam" if self.session is not None else "provider-configuration",
                "timeout_s": self.timeout_s,
                "max_retries": self.max_retries, "max_tool_calls": self.max_tool_calls,
                "max_turns": self.max_turns, "max_tokens": self.max_tokens,
                "backoff_s": self.backoff_s, "max_concurrency": self.max_concurrency}

    def _to_engine(self):
        from ._engine.core.runtime import RuntimeConfig
        from ._engine.core.scheduler import SchedulerConfig
        return RuntimeConfig(provider=self.provider, model_id=self.model, region_name=self.region,
                             endpoint=self.endpoint, api_key=self._api_key, session=self.session,
                             scheduler=SchedulerConfig(**{name: getattr(self, name) for name in SchedulerSettings.model_fields}))


def runtime(*, provider, model=None, region=None, endpoint=None, api_key=None, timeout_s=60.0,
            max_retries=0, max_tool_calls=5, max_turns=6, max_tokens=None, backoff_s=0.0, max_concurrency=1, session=None):
    """Select an actor provider and its controls; optionally borrow an AWS session.

    session selects IAM explicitly, even with a bearer token in the environment.
    Toolkit invocations sharing it are serialized; external concurrent use and
    resource lifetime remain the caller's responsibility. No credentials resolve
    during construction. Serialization omits both the session and API key.
    """
    return _Runtime(provider=provider, model=model, region=region, endpoint=endpoint, api_key=api_key,
                    timeout_s=timeout_s, max_retries=max_retries, max_tool_calls=max_tool_calls,
                    max_turns=max_turns, max_tokens=max_tokens, backoff_s=backoff_s, max_concurrency=max_concurrency, session=session)


class _Framework(ContractModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, arbitrary_types_allowed=True, hide_input_in_errors=True)
    name: Literal["native", "openai-agents", "strands"]
    agent_kwargs: Mapping[str, Any] = Field(default_factory=dict)
    run_kwargs: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("name", mode="before")
    @classmethod
    def graph_is_not_actor(cls, value):
        if value == "langgraph":
            raise ValueError("LangGraph provides orchestration; pass graph=toolkit.Graph(...), not a framework selector")
        return value

    @field_validator("agent_kwargs", "run_kwargs", mode="before")
    @classmethod
    def options_are_mappings(cls, value):
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValueError("Framework options must be dictionaries")
        return dict(value)

    @model_validator(mode="after")
    def boundaries(self):
        _check_framework_options(self.name, self.agent_kwargs, self.run_kwargs)
        object.__setattr__(self, "agent_kwargs", MappingProxyType(dict(self.agent_kwargs)))
        object.__setattr__(self, "run_kwargs", MappingProxyType(dict(self.run_kwargs)))
        return self

    @field_serializer("agent_kwargs", "run_kwargs", when_used="json")
    def describe_sdk_objects(self, value):
        def describe(item):
            if isinstance(item, Mapping):
                return {key: describe(child) for key, child in item.items()}
            if isinstance(item, (list, tuple)):
                return [describe(child) for child in item]
            if item is None or type(item) in {str, int, bool, float}:
                return _json(item)
            return {"python_type": type(item).__module__ + "." + type(item).__qualname__}
        return _redact(describe(value))

    def inspect(self):
        return {"name": self.name, "agent_kwargs": {k: type(v).__name__ for k, v in self.agent_kwargs.items()},
                "run_kwargs": {k: type(v).__name__ for k, v in self.run_kwargs.items()}}

    def _to_engine(self):
        from ._engine.integrations.config import FrameworkConfig
        return FrameworkConfig(name=self.name, agent_kwargs=dict(self.agent_kwargs), run_kwargs=dict(self.run_kwargs))


def framework(name, *, agent_kwargs=None, run_kwargs=None):
    return _Framework(name=name, agent_kwargs={} if agent_kwargs is None else agent_kwargs,
                      run_kwargs={} if run_kwargs is None else run_kwargs)


def _check_framework_options(name, agent_kwargs, run_kwargs):
    if name == "native" and (agent_kwargs or run_kwargs):
        raise ValueError("This adapter does not forward native SDK options")
    from ._engine.integrations.config import RESERVED_AGENT_KWARGS, RESERVED_RUN_KWARGS
    owned = {"runtime", "model", "provider", "api_key", "endpoint", "timeout_s", "max_retries", "max_tokens", "max_turns", "max_tool_calls", "max_concurrency", "backoff_s", "contract", "policy", "limits"}
    if (set(agent_kwargs or {}) & (set(RESERVED_AGENT_KWARGS) | owned)
            or set(run_kwargs or {}) & (set(RESERVED_RUN_KWARGS) | owned)):
        raise ValueError("Framework options cannot override toolkit-owned configuration")
    def nested_conflict(value):
        if isinstance(value, Mapping):
            return bool(set(value) & owned) or any(nested_conflict(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return any(nested_conflict(v) for v in value)
        return False
    for options in (agent_kwargs or {}, run_kwargs or {}):
        for key, value in options.items():
            if key in {"model_settings", "model_kwargs", "generation_config", "run_config", "config"}:
                settings = value if isinstance(value, dict) else vars(value) if hasattr(value, "__dict__") else {}
                settings = {k: v for k, v in settings.items() if v is not None}
                if nested_conflict(settings):
                    raise ValueError("Nested SDK options cannot override toolkit-owned configuration")


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
