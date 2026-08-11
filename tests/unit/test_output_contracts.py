from __future__ import annotations


from agentic_systems.output_contracts import AgenticOutput


def test_output_contract_compact_dict_filters_empty_fields():
    output = AgenticOutput(
        answer="done", data={"x": 1}, runtime={"engine": "python-runtime"}
    )
    full = output.compact_dict()
    compact = output.compact_dict(include_empty=False)
    assert full["schema_version"]
    assert compact["answer"] == "done"
    assert compact["data"] == {"x": 1}
    assert "trace" not in compact
    assert "usage" not in compact
