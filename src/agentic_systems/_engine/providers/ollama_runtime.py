"""Ollama OpenAI-compatible runtime provider.

This provider talks to a running Ollama server through its OpenAI-compatible
API. It does not install, start, pull, or manage Ollama models.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from agentic_systems._engine.contracts import RunPolicy
from agentic_systems._engine.core.results import RunResult
from agentic_systems._engine.defaults import DEFAULT_OLLAMA_API_KEY, DEFAULT_OLLAMA_BASE_URL
from agentic_systems._engine.engines.names import OLLAMA_RUNTIME_ENGINE
from agentic_systems._engine.providers.conformance import ProviderProfile, provider_profile
from agentic_systems._engine.providers.openai_runtime import (
    _build_messages,
    _openai_module,
    _openai_tools,
    _run_chat_loop,
    _run_chat_loop_async,
)


class OllamaRuntimeProvider:
    """OpenAI-compatible provider for a running Ollama server."""

    name = OLLAMA_RUNTIME_ENGINE

    @classmethod
    def profile(cls) -> ProviderProfile:
        return provider_profile(cls.name)

    def __init__(
        self,
        system: Any | None = None,
        *,
        client: Any | None = None,
        async_client: Any | None = None,
    ) -> None:
        self.system = system
        self._client = client
        self._async_client = async_client

    def run(
        self,
        agent: Any,
        input: Any,
        policy: RunPolicy,
        *,
        mode: str = "default",
    ) -> RunResult:
        messages = _build_messages(agent, input)
        runtime = self._runtime(agent)
        tool_defs = _openai_tools(runtime, agent)
        client = self._client if self._client is not None else self._client_from_environment(agent)
        try:
            result = _run_chat_loop(
                client, messages, tool_defs, runtime=runtime, agent=agent,
                policy=policy, mode=mode, runtime_engine=OLLAMA_RUNTIME_ENGINE,
            )
        finally:
            if self._client is None:
                client.close()
        return _as_ollama_result(result)

    async def arun(
        self,
        agent: Any,
        input: Any,
        policy: RunPolicy,
        *,
        mode: str = "default",
    ) -> RunResult:
        runtime = self._runtime(agent)
        messages = _build_messages(agent, input)
        tool_defs = _openai_tools(runtime, agent)
        client = self._async_client if self._async_client is not None else self._async_client_from_environment(agent)
        try:
            result = await _run_chat_loop_async(
                client, messages, tool_defs, runtime=runtime, agent=agent,
                policy=policy, mode=mode, runtime_engine=OLLAMA_RUNTIME_ENGINE,
            )
        finally:
            if self._async_client is None:
                await client.close()
        return _as_ollama_result(result)

    def _runtime(self, agent: Any) -> Any:
        system = getattr(agent, "system", None)
        runtime = system._runtime if system is not None else self.system
        return getattr(runtime, "_runtime", runtime)

    def _connection(self, agent: Any = None) -> dict[str, Any]:
        """Resolve per invocation; never mutate env or cache another actor's key."""
        config = getattr(agent, "runtime_config", None)
        if config is None:
            config = getattr(self.system, "runtime_config", None)
        key = getattr(config, "api_key", None)
        if hasattr(key, "get_secret_value"):
            key = key.get_secret_value()
        return {
            "base_url": getattr(config, "endpoint", None) or _ollama_base_url(),
            "api_key": key if key is not None else _ollama_api_key(),
        }

    def _client_from_environment(self, agent: Any = None) -> Any:
        openai = _openai_module()
        return openai.OpenAI(**self._connection(agent))

    def _async_client_from_environment(self, agent: Any = None) -> Any:
        openai = _openai_module()
        return openai.AsyncOpenAI(**self._connection(agent))


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL


def _ollama_api_key() -> str:
    return os.getenv("OLLAMA_API_KEY") or DEFAULT_OLLAMA_API_KEY


def ollama_environment_snapshot() -> dict[str, Any]:
    """Return non-secret Ollama runtime configuration for diagnostics."""

    from agentic_systems._engine.core.runtime import _load_dotenv

    _load_dotenv()

    base_url = _ollama_base_url()
    model = os.getenv("OLLAMA_MODEL")
    return {
        "base_url": base_url,
        "base_url_configured": bool(os.getenv("OLLAMA_BASE_URL")),
        "model": model,
        "model_configured": bool(model),
        "api_key_configured": bool(os.getenv("OLLAMA_API_KEY")),
    }


def ollama_signal_present() -> bool:
    """Return whether the environment explicitly enables an Ollama server."""

    snapshot: Mapping[str, Any] = ollama_environment_snapshot()
    return bool(snapshot.get("base_url_configured") or snapshot.get("model_configured"))


def _as_ollama_result(result: RunResult) -> RunResult:
    result.engine = OLLAMA_RUNTIME_ENGINE
    result.meta["runtime_engine"] = OLLAMA_RUNTIME_ENGINE
    result.meta["execution_engine"] = OLLAMA_RUNTIME_ENGINE
    result.meta.setdefault("framework_adapter", None)
    if result.meta.get("source_result_type") == "openai.chat.completions":
        result.meta["source_result_type"] = "ollama.openai_compatible.chat.completions"
    return result
