import copy
import json

import pytest

from agentic_systems.agents import Agent
from scripts.semantic_claim_checks import verify_evidence_comparison
from scripts.typed_claim_evaluator import build


EVIDENCE = [
    {"id": "alpha", "ok": True, "output": {"items": [None, 17]}},
    {"id": "beta", "ok": False, "output": None},
]


@pytest.mark.parametrize("index", range(20))
def test_arbitrary_identifiers_paths_and_values_do_not_change_comparison_logic(index):
    key = f"dato/{index}~á"
    record = {"id": f"observación-{index}", key: [{"value": index * 13 - 7}]}
    payload = {
        "records_json": json.dumps([record]),
        "record_id": record["id"],
        "path_json": json.dumps([key, 0, "value"]),
        "expected_json": json.dumps(index * 13 - 7),
    }
    assert verify_evidence_comparison.run(payload).data["status"] == "supported"
    payload["expected_json"] = json.dumps(index * 13 - 6)
    assert verify_evidence_comparison.run(payload).data["status"] == "contradicted"


@pytest.mark.parametrize(
    "identity,path,expected,status",
    [
        ("alpha", ["ok"], True, "supported"),
        ("beta", ["ok"], False, "supported"),
        ("beta", ["ok"], True, "contradicted"),
        ("alpha", ["ok"], 1, "contradicted"),
        ("alpha", ["output", "items", 1], 17, "supported"),
        ("alpha", ["output", "items", 1], "17", "contradicted"),
        ("alpha", ["output", "items", 0], None, "supported"),
        ("beta", ["output"], None, "supported"),
        ("beta", ["missing"], None, "unknown"),
        ("alpha", ["output", "items", 4], None, "unknown"),
        ("alpha", ["output", "items", "1"], 17, "unknown"),
        ("absent", ["ok"], True, "unknown"),
        ("alpha", [], EVIDENCE[0], "supported"),
    ],
)
def test_comparisons_are_typed_and_missing_is_not_false(
    identity, path, expected, status
):
    result = verify_evidence_comparison.run(
        {
            "records_json": json.dumps(EVIDENCE),
            "record_id": identity,
            "path_json": json.dumps(path),
            "expected_json": json.dumps(expected),
        }
    )
    assert result.ok
    assert result.data["status"] == status
    assert result.lineage().steps


@pytest.mark.parametrize(
    "field,value",
    [
        ("records_json", '[{"id":"a","ok":true,"ok":false}]'),
        ("records_json", '[{"id":"a"},{"id":"a"}]'),
        ("records_json", '[{"id":null}]'),
        ("records_json", "{}"),
        ("records_json", "[1]"),
        ("expected_json", "NaN"),
        ("expected_json", "1e9999"),
        ("path_json", "[true]"),
        ("path_json", "[-1]"),
        ("path_json", "[1.0]"),
        ("path_json", "null"),
    ],
)
def test_ambiguous_or_invalid_input_is_rejected(field, value):
    payload = {
        "records_json": json.dumps(EVIDENCE),
        "record_id": "alpha",
        "path_json": '["ok"]',
        "expected_json": "true",
    }
    payload[field] = value
    assert not verify_evidence_comparison.run(payload).ok


def projection(expected=True):
    return {
        "units": [
            {
                "text": "First succeeded.",
                "kind": "equality",
                "comparisons": [
                    {"record_id": "alpha", "path": ["ok"], "expected": expected}
                ],
            },
            {
                "text": "Second failed.",
                "kind": "equality",
                "comparisons": [
                    {"record_id": "beta", "path": ["ok"], "expected": False}
                ],
            },
        ]
    }


def scripted_evaluate(
    monkeypatch,
    plan,
    *,
    faithful=True,
    evidence=None,
    answer="First succeeded. Second failed.",
    framework="native",
):
    calls = []
    original = Agent.run

    def run(self, payload, **kwargs):
        calls.append(self.name)
        if self.name == "compare_fields":
            return original(self, payload, **kwargs)
        if self.name == "project":
            return self.available_tools()[0].run(plan)
        assert self.name == "audit_projection"
        return self.available_tools()[0].run({"faithful": faithful, "clear": True})

    monkeypatch.setattr(Agent, "run", run)
    result = build("ollama-runtime", framework, "offline-model").evaluate(
        answer, EVIDENCE if evidence is None else evidence
    )
    return result, calls


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_mixed_status_claims_use_real_python_tool_execution(monkeypatch, framework):
    result, calls = scripted_evaluate(monkeypatch, projection(), framework=framework)
    assert result["execution_ok"]
    assert result["verdict"]["grounding"] == "pass"
    assert calls == ["project", "audit_projection", "compare_fields", "compare_fields"]
    assert len(result["runs"]) == 4
    assert all(run["lineage"]["steps"] for run in result["runs"])
    assert result["verdict"]["semantic_completeness_proven"] is False


def test_failed_operation_can_support_true_prose_and_wrong_value_is_contradicted(
    monkeypatch,
):
    result, _ = scripted_evaluate(monkeypatch, projection(expected=False))
    assert result["execution_ok"]
    assert result["verdict"]["grounding"] == "fail"
    assert [record["model_status"] for record in result["verdict"]["records"]] == [
        "contradicted",
        "supported",
    ]


def test_extraction_audit_veto_stops_before_comparisons(monkeypatch):
    result, calls = scripted_evaluate(monkeypatch, projection(), faithful=False)
    assert not result["execution_ok"]
    assert result["failure"] == "unfaithful_projection"
    assert calls == ["project", "audit_projection"]


def test_unresolved_and_nonfactual_are_not_converted_to_supported(monkeypatch):
    plan = {
        "units": [
            {
                "text": "Unestablished relationship.",
                "kind": "unresolved",
                "comparisons": [],
            },
            {"text": "Courtesy.", "kind": "nonfactual", "comparisons": []},
        ]
    }
    result, calls = scripted_evaluate(
        monkeypatch, plan, answer="Unestablished relationship. Courtesy."
    )
    assert result["execution_ok"]
    assert result["verdict"]["grounding"] == "unknown"
    assert calls == ["project", "audit_projection"]


@pytest.mark.parametrize(
    "mutation,error",
    [
        (lambda p: p["units"].pop(), "uncovered_answer_text"),
        (
            lambda p: p["units"][0]["comparisons"][0].update(record_id="invented"),
            "invented_evidence_reference",
        ),
        (lambda p: p["units"][0].update(comparisons=[]), "stage_contract_failed"),
        (lambda p: p["units"][0].update(kind="nonfactual"), "stage_contract_failed"),
        (
            lambda p: p["units"][0]["comparisons"].append(
                copy.deepcopy(p["units"][0]["comparisons"][0])
            ),
            "stage_contract_failed",
        ),
    ],
)
def test_invalid_projection_is_not_repaired_silently(monkeypatch, mutation, error):
    plan = projection()
    mutation(plan)
    result, calls = scripted_evaluate(monkeypatch, plan)
    assert not result["execution_ok"]
    assert result["failure"] == error
    assert "compare_fields" not in calls


def test_duplicate_evidence_identity_blocks_before_model_execution(monkeypatch):
    result, calls = scripted_evaluate(
        monkeypatch, projection(), evidence=[EVIDENCE[0], EVIDENCE[0]]
    )
    assert not result["execution_ok"]
    assert result["failure"] == "invalid_evidence_identity"
    assert not calls


def test_missing_field_is_unknown_but_observed_contradiction_dominates(monkeypatch):
    plan = projection(expected=False)
    plan["units"][0]["comparisons"].append(
        {"record_id": "alpha", "path": ["missing"], "expected": None}
    )
    result, _ = scripted_evaluate(monkeypatch, plan)
    assert result["execution_ok"]
    assert result["verdict"]["grounding"] == "fail"
    plan = projection()
    plan["units"][0]["comparisons"][0]["path"] = ["missing"]
    result, _ = scripted_evaluate(monkeypatch, plan)
    assert result["verdict"]["grounding"] == "unknown"
