"""Fixture-owned semantic oracles. Never supplied to a candidate or judge."""

import json

from scripts.claim_evaluator import validate_partition


def _spans(answer, fragments):
    validate_partition(answer, fragments)
    cursor = 0
    spans = []
    for fragment in fragments:
        while cursor < len(answer) and answer[cursor].isspace():
            cursor += 1
        end = cursor + len(fragment.strip())
        spans.append((cursor, end))
        cursor = end
    return spans


def assess_claims(case, evidence, report, annotations):
    """Check annotated obligations even when equal-status clauses are combined.

    This is a test oracle, not an entailment algorithm for arbitrary prose.
    Annotation errors raise; candidate errors return a nonpassing assessment.
    """
    gold = _spans(case["answer"], [item["text"] for item in annotations])
    catalog = {event["id"]: event for event in evidence}
    if len(catalog) != len(evidence):
        raise ValueError("invalid_fixture_evidence")
    for item in annotations:
        required, allowed = set(item["required_ids"]), set(item["allowed_ids"])
        if not required <= allowed <= set(catalog):
            raise ValueError("invalid_fixture_reference")
    problems = []
    if report.get("execution_ok") is not True or not report.get("verdict"):
        return {"passed": False, "problems": ["execution_failed"]}
    verdict = report["verdict"]
    if verdict.get("grounding") != case["expected"]:
        problems.append("aggregate_mismatch")
    if verdict.get("clarity") is not True:
        problems.append("clarity_mismatch")
    try:
        records = verdict["records"]
        spans = _spans(case["answer"], [record["fragment"] for record in records])
        for index, (record, (start, end)) in enumerate(zip(records, spans)):
            covered = [
                i
                for i, (left, right) in enumerate(gold)
                if start <= left and right <= end
            ]
            if (
                not covered
                or gold[covered[0]][0] != start
                or gold[covered[-1]][1] != end
            ):
                problems.append(f"fragment_{index}:annotation_boundary_mismatch")
                continue
            obligations = [annotations[i] for i in covered]
            statuses = {item["status"] for item in obligations}
            if statuses != {record["model_status"]}:
                problems.append(f"fragment_{index}:status_mismatch")
            required = set().union(*(set(item["required_ids"]) for item in obligations))
            allowed = set().union(*(set(item["allowed_ids"]) for item in obligations))
            observed = record["observed_records"]
            ids = [event["id"] for event in observed]
            if len(ids) != len(set(ids)):
                problems.append(f"fragment_{index}:duplicate_citation")
            if not required <= set(ids) or (
                record["model_status"] in {"supported", "contradicted"} and not ids
            ):
                problems.append(f"fragment_{index}:missing_citation")
            if not set(ids) <= allowed:
                problems.append(f"fragment_{index}:irrelevant_citation")
            if any(
                json.dumps(catalog.get(event["id"]), sort_keys=True, allow_nan=False)
                != json.dumps(event, sort_keys=True, allow_nan=False)
                for event in observed
            ):
                problems.append(f"fragment_{index}:evidence_content_mismatch")
    except (KeyError, TypeError, ValueError):
        problems.append("invalid_verdict_structure_or_coverage")
    return {"passed": not problems, "problems": problems}
