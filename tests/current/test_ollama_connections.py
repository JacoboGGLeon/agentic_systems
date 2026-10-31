"""No-network regressions for per-actor Ollama native connections."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import openai
import pydantic
import pytest

import agentic_systems as toolkit
from agentic_systems._engine.contracts import RunPolicy
from agentic_systems._engine.providers import ollama_runtime as module
from agentic_systems._engine.results import RunResult


@pytest.fixture
def sdk(monkeypatch):
    calls, clients = [], []
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://wrong.example/v1")
    monkeypatch.setenv("OLLAMA_API_KEY", "wrong-fixture-key")
    initial = (module._ollama_base_url(), module._ollama_api_key())

    def handler(request):
        payload = json.loads(request.content)
        name = "local" if request.url.host == "local.example" else "cloud"
        assert request.url.host in {"local.example", "cloud.example"}
        assert request.headers["authorization"] == "Bearer " + name + "-fixture-key"
        assert payload["model"] == name + "-model"
        calls.append((name, payload))
        tool_result = next((m for m in reversed(payload["messages"]) if m["role"] == "tool"), None)
        if tool_result is None:
            tool_name = payload["tools"][0]["function"]["name"]
            message = {"role": "assistant", "content": None, "tool_calls": [{"id": "call_" + name,
                "type": "function", "function": {"name": tool_name, "arguments": '{"value":7}'}}]}
        else:
            message = {"role": "assistant", "content": json.dumps({name: 7})}
        return httpx.Response(200, json={"id": "offline", "object": "chat.completion", "created": 0,
            "model": payload["model"], "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    def sync(**kwargs):
        client = openai.OpenAI(**kwargs, max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        clients.append(client)
        return client

    def asynchronous(**kwargs):
        client = openai.AsyncOpenAI(**kwargs, max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        clients.append(client)
        return client

    monkeypatch.setattr(module, "_openai_module", lambda: SimpleNamespace(OpenAI=sync, AsyncOpenAI=asynchronous))
    yield calls, clients
    assert initial == (module._ollama_base_url(), module._ollama_api_key())
    assert clients and all(client.is_closed() for client in clients)


def connection(name):
    return toolkit.runtime(provider="ollama-runtime", model=name + "-model",
        endpoint="https://" + name + ".example/v1", api_key=name + "-fixture-key", max_retries=0,
        timeout_s=10, max_turns=2, max_tool_calls=1)


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_native_local_cloud_system(sdk, parallel, asynchronous):
    @toolkit.tool
    def local_receipt(value: int) -> dict:
        return {"local": value}

    @toolkit.tool
    def cloud_receipt(value: int) -> dict:
        return {"cloud": value}

    local = toolkit.Agent("local", runtime=connection("local"),
        skills=(toolkit.skill(name="local", tools=(local_receipt,)),),
        contract={"output_schema": {"type": "object", "properties": {"local": {"type": "integer"}},
                                   "required": ["local"], "additionalProperties": False}})
    cloud = toolkit.Agent("cloud", runtime=connection("cloud"),
        skills=(toolkit.skill(name="cloud", tools=(cloud_receipt,)),),
        contract={"output_schema": {"type": "object", "properties": {"cloud": {"type": "integer"}},
                                   "required": ["cloud"], "additionalProperties": False}})

    class State(pydantic.BaseModel):
        value: int
        local: int | None = None
        cloud: int | None = None

    def local_step(state):
        return local.run({"value": state.value})

    def cloud_step(state):
        return cloud.run({"value": state.value})

    graph = toolkit.Graph(State)
    graph.add_node("local", local_step)
    graph.add_node("cloud", cloud_step)
    graph.add_edge(toolkit.START, "local")
    if parallel:
        graph.add_edge(toolkit.START, "cloud")
        graph.add_edge("local", toolkit.END)
    else:
        graph.add_edge("local", "cloud")
    graph.add_edge("cloud", toolkit.END)
    system = toolkit.System("two_ollamas", graph=graph).compile()
    for _ in range(2):
        result = asyncio.run(system.arun({"value": 7})) if asynchronous else system.run({"value": 7})
        assert result.ok, result.errors
        assert result.data == {"value": 7, "local": 7, "cloud": 7}
        assert result.check_invariants().ok
        assert len([event for node in result.walk() for event in node.tool_events]) == 2
        assert "fixture-key" not in json.dumps(result.to_dict())
    calls, _ = sdk
    assert len(calls) == 8
    assert [name for name, _ in calls].count("local") == 4


@pytest.mark.parametrize("asynchronous", [False, True])
def test_reused_provider_connection_and_injected_client(monkeypatch, sdk, asynchronous):
    """One provider instance must not cache the first actor's connection."""
    provider = module.OllamaRuntimeProvider(SimpleNamespace(tools=[]))
    monkeypatch.setattr(module, "_openai_tools", lambda *args: [])

    def result(*args, **kwargs):
        return RunResult(text="ok", data={"ok": True})

    async def async_result(*args, **kwargs):
        return result()

    monkeypatch.setattr(module, "_run_chat_loop", result)
    monkeypatch.setattr(module, "_run_chat_loop_async", async_result)

    def actor(name):
        return SimpleNamespace(runtime_config=connection(name)._to_engine(), instructions="", model=name + "-model")

    if asynchronous:
        async def run():
            await asyncio.gather(*(provider.arun(actor(name), {}, RunPolicy()) for name in ("local", "cloud", "local")))
        asyncio.run(run())
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda name: provider.run(actor(name), {}, RunPolicy()), ("local", "cloud", "local")))
    assert sorted(str(client.base_url) for client in sdk[1]) == ["https://cloud.example/v1/", "https://local.example/v1/", "https://local.example/v1/"]
    injected = SimpleNamespace()
    provider = module.OllamaRuntimeProvider(client=injected, async_client=injected)
    provider._runtime = lambda agent: SimpleNamespace(tools=[])
    if asynchronous:
        asyncio.run(provider.arun(actor("cloud"), {}, RunPolicy()))
    else:
        provider.run(actor("cloud"), {}, RunPolicy())
    assert len(sdk[1]) == 3, "An injected client must not be replaced or closed"


def test_connection_precedence_without_environment_mutation(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("OLLAMA_API_KEY", "env-fixture")
    provider = module.OllamaRuntimeProvider()
    assert provider._connection() == {"base_url": "https://env.example/v1", "api_key": "env-fixture"}
    actor = SimpleNamespace(runtime_config=connection("local")._to_engine())
    assert provider._connection(actor) == {"base_url": "https://local.example/v1", "api_key": "local-fixture-key"}
    provider = module.OllamaRuntimeProvider(SimpleNamespace(runtime_config=actor.runtime_config))
    assert provider._connection() == provider._connection(actor)
    monkeypatch.delenv("OLLAMA_BASE_URL")
    monkeypatch.delenv("OLLAMA_API_KEY")
    assert module.OllamaRuntimeProvider()._connection() == {"base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama"}


@pytest.mark.parametrize("endpoint, key, expected_endpoint, expected_key", [
    ("https://explicit.example/v1", None, "https://explicit.example/v1", "env-fixture"),
    (None, pydantic.SecretStr("explicit-fixture"), "https://env.example/v1", "explicit-fixture"),
    (None, pydantic.SecretStr(""), "https://env.example/v1", ""),
])
def test_connection_fields_resolve_independently(monkeypatch, endpoint, key, expected_endpoint, expected_key):
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("OLLAMA_API_KEY", "env-fixture")
    actor = SimpleNamespace(runtime_config=SimpleNamespace(endpoint=endpoint, api_key=key))
    assert module.OllamaRuntimeProvider()._connection(actor) == {"base_url": expected_endpoint, "api_key": expected_key}


def test_async_provider_real_sdk_transport(sdk):
    from agentic_systems._engine.factories import agent

    @toolkit.tool
    def receipt(value: int) -> dict:
        return {"verified": value}

    capability = toolkit.skill(name="receipt", tools=(receipt,))
    actors = [agent(name=name, runtime=connection(name)._to_engine(), skills=[capability._to_engine()])
              for name in ("local", "cloud")]
    provider = module.OllamaRuntimeProvider()

    async def run():
        return await asyncio.gather(*(provider.arun(actor, {"value": 7}, RunPolicy(max_turns=2, max_tool_calls=1))
                                      for actor in actors))

    results = asyncio.run(run())
    assert all(result.ok and len(result.tool_events) == 1 for result in results)
    assert [json.loads(result.text) for result in results] == [{"local": 7}, {"cloud": 7}]
    assert len(sdk[0]) == 4


@pytest.mark.parametrize("asynchronous", [False, True])
def test_owned_client_closes_on_failure(monkeypatch, sdk, asynchronous):
    provider = module.OllamaRuntimeProvider(SimpleNamespace(tools=[]))
    actor = SimpleNamespace(runtime_config=connection("local")._to_engine(), instructions="")
    monkeypatch.setattr(module, "_openai_tools", lambda *args: [])

    def fail(*args, **kwargs):
        raise RuntimeError("controlled offline failure")

    async def async_fail(*args, **kwargs):
        fail()

    monkeypatch.setattr(module, "_run_chat_loop", fail)
    monkeypatch.setattr(module, "_run_chat_loop_async", async_fail)
    with pytest.raises(RuntimeError, match="controlled offline failure"):
        if asynchronous:
            asyncio.run(provider.arun(actor, {}, RunPolicy()))
        else:
            provider.run(actor, {}, RunPolicy())
