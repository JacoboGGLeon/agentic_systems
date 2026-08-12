import asyncio
from types import SimpleNamespace


from agentic_systems import (
    AgentContract,
    RunPolicy,
)
from agentic_systems.providers.base import ToolRegistryRuntime
from agentic_systems.providers.openai_runtime import OpenAIRuntimeProvider


def test_openai_runtime_provider_with_fake_runtime():
    runtime = ToolRegistryRuntime(model_id="model-x")

    @runtime.tool(name="t", description="Echo tool")
    def t(x: int) -> dict[str, int]:
        return {"result": x + 1}

    class FakeResponse:
        def __init__(self, choices):
            self.choices = choices
            self.usage = SimpleNamespace(
                input_tokens=10, output_tokens=5, total_tokens=15
            )

    class FakeMessage:
        def __init__(self, content="", tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    class FakeToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.function = SimpleNamespace(name=name, arguments=arguments)

    class FakeClient:
        def __init__(self):
            self.calls = 0
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                tool_call = FakeToolCall("call_1", "t", '{"x": 41}')
                return FakeResponse(
                    [SimpleNamespace(message=FakeMessage(tool_calls=[tool_call]))]
                )
            return FakeResponse(
                [SimpleNamespace(message=FakeMessage(content="openai final"))]
            )

    class FakeAsyncClient:
        def __init__(self, sync_client):
            self.sync_client = sync_client
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        async def create(self, **kwargs):
            return self.sync_client.create(**kwargs)

    fake_system = SimpleNamespace(_runtime=runtime, model="model-x")
    agent = SimpleNamespace(
        name="oa",
        instructions="inst",
        tools=("t",),
        model=None,
        contract=AgentContract(),
        system=fake_system,
        framework="openai-agents",
    )
    client = FakeClient()
    engine = OpenAIRuntimeProvider(
        fake_system, client=client, async_client=FakeAsyncClient(client)
    )
    result = engine.run(agent, {"x": 1}, RunPolicy(), mode="audit")
    assert result.text == "openai final"
    assert result.engine == "openai-runtime"
    assert result.meta["framework"] == "openai-agents"
    assert result.meta["execution_engine"] == "openai-runtime"
    assert result.tool_events[0].name == "t"
    assert result.tool_events[0].output["result"] == 42
    async_result = asyncio.run(engine.arun(agent, {"x": 2}, RunPolicy(), mode="audit"))
    assert async_result.text == "openai final"
