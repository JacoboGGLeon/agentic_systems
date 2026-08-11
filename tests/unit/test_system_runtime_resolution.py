from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace


import agentic_systems.core.runtime as runtime_core_mod

system_mod = importlib.import_module("agentic_systems.system")


def test_system_auto_provider_and_runtime_copy(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.setattr(
        runtime_core_mod, "_module_available", lambda name: name == "openai"
    )
    fake_openai = ModuleType("agentic_systems.providers.openai_runtime")
    fake_openai.OpenAIRuntimeProvider = object
    monkeypatch.setitem(
        sys.modules, "agentic_systems.providers.openai_runtime", fake_openai
    )
    assert (
        system_mod._resolve_auto_provider(None, None, ("openai-runtime",))
        == "openai-runtime"
    )

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AWS_REGION", "us-test-1")
    monkeypatch.setenv("AWS_PROFILE", "test-profile")
    monkeypatch.setattr(
        runtime_core_mod, "_module_available", lambda name: name == "boto3"
    )
    fake_bedrock = ModuleType("agentic_systems.providers.bedrock_runtime")

    class FakeBedrockRuntime:
        def __init__(
            self,
            *,
            model_id,
            region_name,
            max_tokens_default,
            temperature_default,
            disable_openai_runtime_tracing,
        ):
            self.model_id = model_id
            self.region_name = region_name or "us-test-1"
            self.max_tokens_default = max_tokens_default
            self.temperature_default = temperature_default
            self.disable_openai_runtime_tracing = disable_openai_runtime_tracing
            self._tools = {}

    fake_bedrock.BedrockRuntime = FakeBedrockRuntime
    monkeypatch.setitem(
        sys.modules, "agentic_systems.providers.bedrock_runtime", fake_bedrock
    )
    monkeypatch.setattr(system_mod, "BedrockRuntime", FakeBedrockRuntime, raising=False)
    assert system_mod._resolve_auto_provider(None, "us-test-1") == "bedrock-runtime"

    system = system_mod.AgenticSystem(model="m", region="r")
    previous = SimpleNamespace(
        max_tokens_default=11,
        temperature_default=0.5,
        _tools={"x": object()},
        runtime="runtime-client",
        bedrock="bedrock-client",
        sts="sts-client",
    )
    system._runtime = previous
    hydrated = system._ensure_bedrock_runtime()
    assert hydrated._tools == previous._tools
    assert hydrated.runtime == "runtime-client"
    assert hydrated.bedrock == "bedrock-client"
    assert hydrated.sts == "sts-client"
