from __future__ import annotations

import importlib

import pytest

import agentic_systems.utils as utils
from agentic_systems.results import RunResult

system_mod = importlib.import_module("agentic_systems.system")


def test_utils_jsonable_root_and_show_paths(capsys):
    output = utils.agent_output(
        RunResult(text="hello world" * 20, data={}, ok=True, engine="openai-runtime"),
        max_string_chars=12,
    )
    assert output["summary"]["answer_preview"]["chars"] > 12

    serialized = {
        "ok": True,
        "engine": "python-runtime",
        "tool_events": [],
        "data": {"x": 1},
    }
    assert utils._coerce_compare_item(serialized)["run_ok"] is True
    assert utils._coerce_compare_item({"plain": "value"}) == {"plain": "value"}

    assert utils.chain_history_summary(["raw"])[0]["value"] == "raw"
    fields = utils._extract_output_fields(
        object(),
        result_dict={},
        answer_text="",
        data={"fields": {"a": 1}},
        tools=[],
        fields_mapper=None,
    )
    assert fields == {"a": 1}
    with pytest.raises(TypeError, match="fields_mapper"):
        utils._extract_output_fields(
            object(),
            result_dict={},
            answer_text="",
            data={},
            tools=[],
            fields_mapper=lambda *_: "bad",
        )

    assert utils._answer_preview("x" * 30, max_string_chars=5)["preview"]
    assert utils._user_facing_answer_text("", {}, {}) == ""
    assert utils._user_facing_answer_text('{"steps": []}', {"steps": []}, {}) == ""
    assert utils._looks_like_json_object("{bad") is False
    assert utils._coerce_field_value("not-a-number") == "not-a-number"

    utils.show({"x": 1}, title="JSON fallback")
    assert "JSON fallback" in capsys.readouterr().out
