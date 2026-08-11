from __future__ import annotations

from dataclasses import dataclass

import pytest

from agentic_systems.final_answer import (
    OutputSchema,
    final_answer,
    normalize_output,
    output_schema,
)
import agentic_systems.results as results_module
from agentic_systems.results import RunResult


@dataclass
class PayloadDataclass:
    value: int
    label: str


class ModelDumpPayload:
    def model_dump(self, mode="json"):
        assert mode == "json"
        return {"value": 7, "label": "model"}


class BadJson:
    def __str__(self):
        return "bad-json-object"


def test_final_answer_schema_normalization_and_projection_edges():
    assert OutputSchema.coerce(None) is None
    existing = OutputSchema(fields=("answer",))
    assert OutputSchema.coerce(existing) is existing
    assert OutputSchema.coerce({"fields": ["value"]}).project({"value": 1}) == {
        "value": 1
    }
    with pytest.raises(TypeError):
        OutputSchema.coerce(object())

    assert normalize_output(ModelDumpPayload()) == {"value": 7, "label": "model"}
    assert normalize_output(PayloadDataclass(3, "dc")) == {"value": 3, "label": "dc"}
    assert normalize_output([{"a": 1}]) == {"rows": [{"a": 1}]}
    assert normalize_output([1, 2]) == {"items": [1, 2]}
    assert normalize_output("hello") == {"value": "hello"}
    assert normalize_output(None) == {}
    assert normalize_output(42) == {"value": 42}

    passthrough = output_schema()
    assert passthrough.project({"x": 1}) == {"x": 1}
    many = output_schema(fields=["id", "name"], many=True, root_key="records")
    assert many.project({"data": [{"id": 1, "fields": {"name": "Ada"}}]}) == {
        "records": [{"id": 1, "name": "Ada"}]
    }
    aliases = output_schema(fields=["answer"], aliases={"answer": "value"})
    assert aliases.project({"last": {"value": 99}}) == {"answer": 99}
    assert output_schema(fields=["missing"]).project({"x": 1}) == {"missing": None}
    with pytest.raises(KeyError):
        output_schema(fields=["missing"], required=True).project({"x": 1})

    assert final_answer({}, text=" fallback ") == {"text": "fallback"}
    assert final_answer({}, text=" ") == {}
    assert final_answer(
        {"rows": [{"id": 1}]}, schema={"fields": ["id"], "many": True}
    ) == {"rows": [{"id": 1}]}


def test_final_answer_and_results_private_edges(monkeypatch):
    assert output_schema(fields=["x"], many=True).project({"x": 1}) == {
        "rows": [{"x": 1}]
    }
    assert output_schema(fields=["x"], many=True).project({}) == {"rows": []}

    class RawOutputEvent:
        id = "raw"
        name = "raw"
        input = {}
        ok = True
        error = None
        duration_ms = None

        def model_dump(self, mode="json"):
            assert mode == "json"
            return {
                "id": "raw",
                "name": "raw",
                "input": {},
                "output": "scalar",
                "ok": True,
                "error": None,
                "duration_ms": None,
            }

    normalized = results_module._normalize_tool_event(RawOutputEvent())
    assert normalized["output"] == {"value": "scalar"}

    usage = results_module._usage_totals(
        [
            {
                "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
                "client_duration_ms": "oops",
            }
        ]
    )
    assert usage["total_tokens"] == 3

    def fake_tool_expectation(called, expectation):
        return {"expectation": expectation, "issues": [{}]}

    monkeypatch.setattr(
        results_module, "validate_tool_expectation", fake_tool_expectation
    )
    validation = RunResult(tool_events=[]).validate(
        {"tool_expectation": {"rule": "custom"}}
    )
    assert validation.issues[0].code == "tool_expectation_failed"
