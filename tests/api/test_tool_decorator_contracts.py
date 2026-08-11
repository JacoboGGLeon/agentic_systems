"""Tests for the public module-level @tool decorator."""

from __future__ import annotations

from pydantic import BaseModel

from agentic_systems import AgenticSystem, Tool, tool
from agentic_systems.errors import ToolContractError
from agentic_systems.tools import tool as package_tool


class SumInput(BaseModel):
    a: int
    b: int


class SumOutput(BaseModel):
    result: int


def test_top_level_tool_decorator_returns_tool_instance() -> None:
    @tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos enteros."""
        return {"result": a + b}

    assert isinstance(sumar, Tool)
    assert sumar.name == "sumar"
    assert sumar.description == "Suma dos enteros."
    assert sumar.info()["description_source"] == "docstring"
    result = sumar.run({"a": 17, "b": 25})
    assert result.ok is True
    assert result.data == {"result": 42}
    assert result.tool_events[0].name == "sumar"


def test_tool_decorator_accepts_configuration_and_pydantic_contracts() -> None:
    @tool(name="math.sum", description="Suma validada.", input_schema=SumInput, output_schema=SumOutput)
    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    assert add.name == "math.sum"
    assert add.describe() == "Tool `math.sum`: Suma validada."
    assert add.info()["description_source"] == "decorator"
    result = add.run({"a": "20", "b": 22})
    assert result.ok is True
    assert result.data == {"result": 42}
    assert add.info()["input_schema"]["name"] == "SumInput"
    assert add.info()["output_schema"]["name"] == "SumOutput"


def test_tool_decorator_supports_non_strict_normalization() -> None:
    @tool(strict=False)
    def keywords(text: str) -> list[str]:
        return text.split()

    result = keywords.run({"text": "agentic systems"})
    assert result.ok is True
    assert result.data == {"items": ["agentic", "systems"]}


def test_tool_decorator_rejects_non_callables() -> None:
    try:
        tool(123)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "callables" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected TypeError")


def test_package_level_tool_export_matches_top_level_export() -> None:
    assert package_tool is tool


def test_system_tool_keeps_compatibility_behavior_and_public_wrapper() -> None:
    system = AgenticSystem(model="qwen.qwen3-32b-v1:0", region="us-east-1")

    @system.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos números."""
        return {"result": a + b}

    assert callable(sumar)
    assert "sumar" in system.tool_names
    assert "sumar" in system.public_tools
    assert isinstance(system.public_tools["sumar"], Tool)
    assert system.public_tools["sumar"].description == "Suma dos números."
    assert system.public_tools["sumar"].run({"a": 17, "b": 25}).data == {"result": 42}
    assert system.execute_tool("sumar", {"a": 17, "b": 25}).data == {"result": 42}


def test_system_tool_still_raises_tool_contract_error_in_strict_mode() -> None:
    system = AgenticSystem(model="qwen.qwen3-32b-v1:0", region="us-east-1")

    try:
        @system.tool
        def bad(text: str) -> list[str]:
            return text.split()
    except ToolContractError as exc:
        assert "must be annotated as returning dict" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected ToolContractError")
