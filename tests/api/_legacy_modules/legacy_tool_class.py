"""Tests for the public Tool class."""

from __future__ import annotations

import dataclasses

from pydantic import BaseModel

from agentic_systems import Tool
from agentic_systems.tools.tool import CheckResult, _normalize_to_dict


class SumInput(BaseModel):
    a: int
    b: int


class SumOutput(BaseModel):
    result: int


class ValueOutput(BaseModel):
    value: int


@dataclasses.dataclass
class Metric:
    name: str
    value: float


def test_tool_runs_simple_dict_function_and_reports_info() -> None:
    def sumar(a: int, b: int) -> dict:
        """Suma dos enteros."""
        return {"result": a + b}

    tool = Tool(name="sumar", function=sumar, metadata={"domain": "math"})
    result = tool.run({"a": 17, "b": 25})

    assert result.ok is True
    assert result.data == {"result": 42}
    assert result.engine == "python-direct"
    assert result.mode == "tool"
    assert result.tool_events[0].name == "sumar"
    assert result.tool_events[0].input == {"a": 17, "b": 25}
    assert result.tool_events[0].output == {"data": {"result": 42}}
    assert tool.info()["metadata"] == {"domain": "math"}
    assert tool.info()["function"] == "sumar"
    assert tool.info()["description"] == "Suma dos enteros."
    assert tool.info()["description_source"] == "docstring"
    assert tool.describe() == "Tool `sumar`: Suma dos enteros."


def test_tool_rejects_non_dict_output_in_strict_mode_as_run_result() -> None:
    def keywords(text: str) -> dict:
        """Returns a non-dict on purpose despite the annotation."""
        return [token.lower() for token in text.split()]  # type: ignore[return-value]

    tool = Tool(name="keywords", function=keywords)
    result = tool.run({"text": "Bedrock Agents"})

    assert result.ok is False
    assert result.data["error_type"] == "ToolContractError"
    assert "returned list" in result.data["message"]
    assert result.tool_events[0].ok is False
    assert result.tool_events[0].error == result.data


def test_tool_validates_pydantic_input_and_output_with_kwargs() -> None:
    def sumar(a: int, b: int) -> dict:
        """Suma dos enteros."""
        return {"result": a + b}

    tool = Tool(name="sumar", function=sumar, input_schema=SumInput, output_schema=SumOutput)
    result = tool.run({"a": "20", "b": 22})

    assert result.ok is True
    assert result.data == {"result": 42}
    assert tool.info()["input_schema"]["name"] == "SumInput"
    assert tool.info()["output_schema"]["name"] == "SumOutput"


def test_tool_accepts_pydantic_model_input_object() -> None:
    def sumar(payload: SumInput) -> dict:
        """Suma desde un contrato."""
        return {"result": payload.a + payload.b}

    tool = Tool(name="sumar_model", function=sumar, input_schema=SumInput, output_schema=SumOutput)
    result = tool.run(SumInput(a=40, b=2))

    assert result.ok is True
    assert result.data == {"result": 42}


def test_tool_validates_pydantic_output_model_return() -> None:
    def answer() -> SumOutput:
        """Return model output."""
        return SumOutput(result=42)

    tool = Tool(name="answer", function=answer, output_schema=SumOutput)
    result = tool.run()

    assert result.ok is True
    assert result.data == {"result": 42}


def test_tool_check_reports_missing_function_and_type_hints() -> None:
    empty = Tool(name="empty")
    assert isinstance(empty.check(), CheckResult)
    missing = empty.run()
    assert missing.ok is False
    assert missing.data["error_type"] == "ValueError"
    assert "missing_function" in missing.data["message"]

    def bad(a) -> list:  # noqa: ANN001
        return [a]

    tool = Tool(name="bad", function=bad)
    validation = tool.check()
    codes = {issue.code for issue in validation.issues}

    assert {"missing_parameter_annotation", "return_annotation_must_be_dict"} <= codes
    assert tool.run({"a": 1}).ok is False


def test_tool_input_and_call_errors_are_structured() -> None:
    def sumar(a: int, b: int) -> dict:
        return {"result": a + b}

    tool = Tool(name="sumar", function=sumar, input_schema=SumInput)
    invalid = tool.run({"a": 1})
    assert invalid.ok is False
    assert invalid.data["error_type"] == "ValidationError"

    no_schema = Tool(name="sumar_no_schema", function=sumar)
    scalar = no_schema.run(1)
    assert scalar.ok is False
    assert scalar.data["error_type"] == "TypeError"
    assert "expected dict input" in scalar.data["message"]

    extra = no_schema.run({"a": 1, "b": 2, "c": 3})
    assert extra.ok is False
    assert extra.data["error_type"] == "TypeError"


def test_tool_non_strict_normalizes_common_outputs_and_context_meta() -> None:
    def tags(text: str) -> list[str]:
        return text.split()

    list_tool = Tool(name="tags", function=tags, strict=False)
    assert list_tool.run({"text": "a b"}, context={"request_id": "r1"}).data == {"items": ["a", "b"]}
    assert list_tool.run({"text": "a b"}, context={"request_id": "r1"}).meta["context_type"] == "dict"

    def text() -> str:
        return "ok"

    def none() -> None:
        return None

    def model() -> ValueOutput:
        return ValueOutput(value=7)

    def metric() -> Metric:
        return Metric(name="coverage", value=1.0)

    def number(value: int) -> int:
        return value

    assert Tool(name="text", function=text, strict=False).run().data == {"text": "ok"}
    assert Tool(name="none", function=none, strict=False).run().data == {"ok": True}
    assert Tool(name="model", function=model, strict=False).run().data == {"value": 7}
    assert Tool(name="metric", function=metric, strict=False).run().data == {"name": "coverage", "value": 1.0}
    assert Tool(name="number", function=number, strict=False).run(42).data == {"value": 42}


def test_tool_constructor_validation_and_describe_without_description() -> None:
    assert Tool(name="plain").describe() == "Tool `plain`"

    try:
        Tool(name=" ")
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected ValueError")

    try:
        Tool(name="bad_function", function=123)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "callable" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected TypeError")

    try:
        Tool(name="bad_schema", input_schema=dict)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "input_schema" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected TypeError")

    try:
        Tool(name="bad_output_schema", output_schema=dict)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "output_schema" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected TypeError")


def test_private_normalizer_keeps_dicts() -> None:
    assert _normalize_to_dict({"x": 1}) == {"x": 1}
