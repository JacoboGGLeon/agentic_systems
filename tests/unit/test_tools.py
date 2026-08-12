from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib

import pytest
from pydantic import BaseModel

from agentic_systems.tools import Tool, tool as tool_decorator

tool_module = importlib.import_module("agentic_systems.tools.tool")


class PayloadModel(BaseModel):
    value: int


@dataclass
class DataConfig:
    path: Path


def test_tool_call_schema_alias_and_context_meta_edges():
    def one(payload: dict) -> dict:
        return {"seen": payload}

    def zero() -> dict:
        return {"ok": True}

    def multi_fn(a: int, b: int) -> dict:
        return {"sum": a + b}

    one_arg = Tool(name="one", function=one)
    assert one_arg.run({"a": 1}).data == {"seen": {"a": 1}}
    assert one_arg.run(PayloadModel(value=2)).data["seen"].value == 2

    no_arg = Tool(name="zero", function=zero)
    assert no_arg.run({"ignored": True}).data == {"ok": True}

    multi = Tool(name="multi", function=multi_fn)
    assert multi.run({"a": 2, "b": 3}).data == {"sum": 5}
    bad_result = multi.run("bad")
    assert bad_result.ok is False
    assert bad_result.data["error_type"] == "TypeError"

    class InSchema(BaseModel):
        x: int

    schema_tool = tool_decorator(
        name="schema", input_schema=InSchema, input_model=InSchema
    )(lambda x: {"x": x})
    assert schema_tool.input_schema is InSchema
    with pytest.raises(ValueError):
        tool_decorator(
            name="bad_schema", input_schema=InSchema, input_model=PayloadModel
        )(lambda x: {"x": x})
    with pytest.raises(TypeError):
        tool_decorator(name="bad_model", input_schema=dict)(lambda x: {"x": x})

    context_result = one_arg.run({"a": 1}, context={"user_prompt": "hello"})
    assert context_result.meta["input"] == "hello"
