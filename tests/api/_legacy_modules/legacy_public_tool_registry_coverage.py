from __future__ import annotations

from agentic_systems import AgenticSystem


def test_public_tool_registry_mapping_and_iteration() -> None:
    system = AgenticSystem(model="dummy", region="us-east-1")

    @system.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos enteros."""
        return {"result": a + b}

    registry = system.public_tools
    assert len(registry) == 1
    assert "sumar" in registry
    assert registry["sumar"].name == "sumar"
    assert [tool.name for tool in registry] == ["sumar"]
    assert list(registry.keys()) == ["sumar"]
    assert [tool.name for tool in registry.values()] == ["sumar"]
    assert [(name, tool.name) for name, tool in registry.items()] == [("sumar", "sumar")]
    assert registry.get("sumar").name == "sumar"
    assert registry.get("missing", "fallback") == "fallback"
    assert registry.to_dict()["sumar"].name == "sumar"
    assert "PublicToolRegistry" in repr(registry)
