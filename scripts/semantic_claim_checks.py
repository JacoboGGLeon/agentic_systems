"""Application-level factual checks; not a natural-language entailment solver."""

import json
from typing import Any

import agentic_systems as toolkit


def parse_json_value(text: str):
    """Reject ambiguous objects and non-JSON numeric constants."""

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("nonfinite_json_number")

    value = json.loads(
        text, object_pairs_hook=object_pairs, parse_constant=invalid_constant
    )
    # Also rejects finite-looking input whose exponent overflows to infinity.
    json.dumps(value, allow_nan=False)
    return value


@toolkit.tool
def verify_evidence_comparison(
    records_json: str, record_id: str, path_json: str, expected_json: str
) -> dict:
    """Compare an application-owned observation with a typed equality claim.

    Missing evidence is unknown, not contradiction. A failed operation can
    support a true claim of failure. This checks data, not prose fidelity.
    """
    records = parse_json_value(records_json)
    path = parse_json_value(path_json)
    expected = parse_json_value(expected_json)
    if not isinstance(records, list) or any(
        not isinstance(record, dict) for record in records
    ):
        raise ValueError("evidence_records_required")
    ids = [record.get("id") for record in records]
    if any(type(identity) is not str or not identity for identity in ids) or len(
        ids
    ) != len(set(ids)):
        raise ValueError("invalid_evidence_identity")
    if not isinstance(path, list) or any(
        not (type(part) is str or (type(part) is int and part >= 0)) for part in path
    ):
        raise ValueError("invalid_evidence_path")
    reference = {"record_id": record_id, "path": path, "expected": expected}
    catalog = dict(zip(ids, records))
    if record_id not in catalog:
        return dict(reference, status="unknown", reason="missing_record")
    observed = catalog[record_id]
    for part in path:
        if isinstance(observed, dict) and type(part) is str and part in observed:
            observed = observed[part]
        elif isinstance(observed, list) and type(part) is int and part < len(observed):
            observed = observed[part]
        else:
            return dict(reference, status="unknown", reason="missing_path")
    same = json.dumps(observed, sort_keys=True, allow_nan=False) == json.dumps(
        expected, sort_keys=True, allow_nan=False
    )
    return dict(
        reference,
        observed=observed,
        status="supported" if same else "contradicted",
        reason="exact_match" if same else "value_mismatch",
    )


def check_required_claims(
    evidence: dict[str, Any], claims: dict[str, Any], required_fields: tuple[str, ...]
) -> dict:
    """Run the public deterministic Agent; missing/extra claims fail closed.

    Required fields and evidence are application-owned, never selected by the judge.
    This verifies typed facts only, not completeness or fidelity of prose extraction.
    """
    if not required_fields or len(set(required_fields)) != len(required_fields):
        raise ValueError("nonempty_unique_obligations_required")
    if set(claims) != set(required_fields):
        return dict(
            passed=False,
            reason="claim_inventory_mismatch",
            checks=[],
            missing=sorted(set(required_fields) - set(claims)),
            unexpected=sorted(set(claims) - set(required_fields)),
        )
    agent = toolkit.agent(
        name="required_fact_checker",
        runtime=toolkit.runtime(provider="python-runtime"),
        tools=[verify_evidence_field],
    )
    checks = []
    for field in required_fields:
        result = agent.run(
            {
                "tool": "verify_evidence_field",
                "input": {
                    "evidence_json": json.dumps(evidence, allow_nan=False),
                    "field": field,
                    "claimed_json": json.dumps(claims[field], allow_nan=False),
                },
            }
        )
        events = result.normalized()["tools"]
        valid = (
            result.ok
            and len(events) == 1
            and events[0]["ok"]
            and events[0]["name"] == "verify_evidence_field"
        )
        checks.append(
            dict(
                passed=bool(valid and events[0]["output"].get("supported") is True),
                result=result.normalized(),
                lineage=result.lineage().model_dump(mode="json"),
            )
        )
    return dict(passed=all(check["passed"] for check in checks), checks=checks)


@toolkit.tool
def verify_evidence_field(evidence_json: str, field: str, claimed_json: str) -> dict:
    """Compare a typed claim with an explicit evidence field, without coercion.

    Callers must supply authenticated/selected evidence and the correct field.
    Passing this check does not establish that prose was faithfully extracted.
    """
    evidence = json.loads(evidence_json)
    claimed = json.loads(claimed_json)
    if not isinstance(evidence, dict):
        raise ValueError("evidence_mapping_required")
    if field not in evidence:
        return dict(supported=False, reason="missing_evidence_field", field=field)
    observed = evidence[field]
    same = json.dumps(observed, sort_keys=True, allow_nan=False) == json.dumps(
        claimed, sort_keys=True, allow_nan=False
    )
    return dict(
        supported=same,
        reason="exact_match" if same else "evidence_value_mismatch",
        field=field,
        observed=observed,
        claimed=claimed,
    )
