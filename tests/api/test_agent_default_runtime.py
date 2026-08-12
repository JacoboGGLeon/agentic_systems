from __future__ import annotations


def test_agent_default_is_cloud_configuration_until_bound_to_a_system():
    import pytest

    import agentic_systems as lab

    @lab.tool
    def sumar(a: int, b: int) -> dict:
        return {"result": a + b}

    agent = lab.Agent(name="portable_agent", tools=[sumar])

    assert agent.engine == lab.BEDROCK_RUNTIME_ENGINE
    with pytest.raises(RuntimeError, match=r"bind\(system\)"):
        agent.run({"a": 1, "b": 2}, mode="eval")
