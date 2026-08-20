"""vLLM OpenAI-compatible runtime provider.

This provider talks to a running vLLM OpenAI-compatible server. It does not
import or start vLLM itself, keeping the base package safe for local, CI and
non-GPU environments.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from agentic_systems.contracts import RunPolicy
from agentic_systems.defaults import DEFAULT_VLLM_API_KEY, DEFAULT_VLLM_BASE_URL
from agentic_systems.core.results import RunResult
from agentic_systems.engines.names import VLLM_RUNTIME_ENGINE
from agentic_systems.providers.conformance import ProviderProfile, provider_profile
from agentic_systems.providers.openai_runtime import (
    _build_messages,
    _failure,
    _openai_module,
    _openai_tools,
    _run_chat_loop,
    _run_chat_loop_async,
)



class VLLMRuntimeProvider:
    """OpenAI-compatible provider for a running vLLM server."""

    name = VLLM_RUNTIME_ENGINE

    @classmethod
    def profile(cls) -> ProviderProfile:
        return provider_profile(cls.name)

    def __init__(self, system: Any | None = None, *, client: Any | None = None, async_client: Any | None = None) -> None:
        self.system = system
        self._client = client
        self._async_client = async_client

    def run(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        messages = _build_messages(agent, input)
        runtime = self._runtime(agent)
        tool_defs = _openai_tools(runtime, agent)
        if not tool_defs:
            return self._failure("VLLMRuntimeProvider needs at least one concrete Tool on the agent.", agent, mode, "missing_tools")

        client = self._client or self._client_from_environment()
        result = _run_chat_loop(
            client,
            messages,
            tool_defs,
            runtime=runtime,
            agent=agent,
            policy=policy,
            mode=mode,
            runtime_engine=VLLM_RUNTIME_ENGINE,
        )
        return _as_vllm_result(result)

    async def arun(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        runtime = self._runtime(agent)
        messages = _build_messages(agent, input)
        tool_defs = _openai_tools(runtime, agent)
        if not tool_defs:
            return self._failure("VLLMRuntimeProvider needs at least one concrete Tool on the agent.", agent, mode, "missing_tools")

        client = self._async_client or self._async_client_from_environment()
        result = await _run_chat_loop_async(
            client,
            messages,
            tool_defs,
            runtime=runtime,
            agent=agent,
            policy=policy,
            mode=mode,
            runtime_engine=VLLM_RUNTIME_ENGINE,
        )
        return _as_vllm_result(result)

    def _runtime(self, agent: Any) -> Any:
        runtime = getattr(agent, "system", None)._runtime if getattr(agent, "system", None) is not None else self.system
        return getattr(runtime, "_runtime", runtime)

    def _client_from_environment(self) -> Any:
        openai = _openai_module()
        return openai.OpenAI(
            base_url=_vllm_base_url(),
            api_key=_vllm_api_key(),
        )

    def _async_client_from_environment(self) -> Any:
        openai = _openai_module()
        return openai.AsyncOpenAI(
            base_url=_vllm_base_url(),
            api_key=_vllm_api_key(),
        )

    def _failure(self, message: str, agent: Any, mode: str, code: str) -> RunResult:
        result = _failure(message, agent, mode, code, meta={"execution_engine": VLLM_RUNTIME_ENGINE})
        result.engine = VLLM_RUNTIME_ENGINE
        result.meta["runtime_engine"] = VLLM_RUNTIME_ENGINE
        result.meta.update({"framework": getattr(agent, "framework", None), "framework_requested": getattr(agent, "framework", None), "framework_adapter": None})
        return result


def _vllm_base_url() -> str:
    return os.getenv("VLLM_BASE_URL") or DEFAULT_VLLM_BASE_URL


def _vllm_api_key() -> str:
    return os.getenv("VLLM_API_KEY") or DEFAULT_VLLM_API_KEY


def vllm_environment_snapshot() -> dict[str, Any]:
    """Return non-secret vLLM runtime configuration for diagnostics."""

    from agentic_systems.core.runtime import _load_dotenv

    _load_dotenv()

    base_url = _vllm_base_url()
    model = os.getenv("VLLM_MODEL")
    return {
        "base_url": base_url,
        "base_url_configured": bool(os.getenv("VLLM_BASE_URL")),
        "model": model,
        "model_configured": bool(model),
        "api_key_configured": bool(os.getenv("VLLM_API_KEY")),
    }


def vllm_signal_present() -> bool:
    """Return whether the environment explicitly points to a vLLM server."""

    snapshot: Mapping[str, Any] = vllm_environment_snapshot()
    return bool(snapshot.get("base_url_configured"))


def _as_vllm_result(result: RunResult) -> RunResult:
    result.engine = VLLM_RUNTIME_ENGINE
    result.meta["runtime_engine"] = VLLM_RUNTIME_ENGINE
    result.meta["execution_engine"] = VLLM_RUNTIME_ENGINE
    result.meta.setdefault("framework_adapter", None)
    if result.meta.get("source_result_type") == "openai.chat.completions":
        result.meta["source_result_type"] = "vllm.openai_compatible.chat.completions"
    return result
