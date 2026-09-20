"""Application-owned citation catalog; reference validity is not entailment."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reference: str = Field(min_length=1)
    value_json: str = Field(min_length=1)


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def evidence_catalog(packet: dict[str, Any]) -> dict[str, str]:
    """Generate local references from observed content, never judge-selected URLs."""
    catalog = {"/answer": canonical(packet["answer"])}

    def visit(value: Any, path: str) -> None:
        # Every actual field below observed execution evidence is addressable.
        # Requirements and audit instructions are deliberately not evidence.
        catalog[path] = canonical(value)
        if isinstance(value, dict):
            for key, child in value.items():
                token = key.replace("~", "~0").replace("/", "~1")
                visit(child, path + "/" + token)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + "/" + str(index))

    for index, stage in enumerate(packet.get("execution_evidence", [])):
        visit(stage, f"/execution_evidence/{index}")
    return catalog


def check_references(
    packet: dict[str, Any], assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    catalog = evidence_catalog(packet)  # Recompute; do not trust an embedded catalog.
    issues = []
    if not assessments:
        issues.append(dict(reason="missing_assessments"))
    for assessment in assessments:
        citations = assessment.get("references", [])
        if not citations:
            issues.append(
                dict(criterion=assessment["criterion"], reason="missing_reference")
            )
        seen = set()
        for raw in citations:
            citation = EvidenceCitation.model_validate(raw)
            reason = None
            if citation.reference in seen:
                reason = "duplicate_reference"
            elif citation.reference not in catalog:
                reason = "unknown_reference"
            else:
                try:
                    actual = canonical(json.loads(citation.value_json))
                except (ValueError, TypeError):
                    reason = "invalid_cited_json"
                else:
                    if actual != catalog[citation.reference]:
                        reason = "cited_value_mismatch"
            seen.add(citation.reference)
            if reason:
                issues.append(
                    dict(
                        criterion=assessment["criterion"],
                        reference=citation.reference,
                        reason=reason,
                    )
                )
    return dict(passed=not issues, issues=issues, semantic_relevance_verified=False)
