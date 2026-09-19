"""Application-local evidence projection. Not a public memory/context API."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from agentic_systems import RunResult


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class EvidenceSelection:
    source_execution_id: str
    tool_event_id: str
    owner_execution_id: str
    payload_json: str

    def payload(self) -> dict[str, Any]:
        """Each read returns a new object, isolated from historical evidence."""
        return json.loads(self.payload_json)


def select_single_tool_result(
    source: RunResult,
    *,
    tool_name: str,
    expected_input: dict[str, Any],
    observed_output: dict[str, Any],
) -> EvidenceSelection:
    """Require one observed action; identical ancestor projections are not calls.

    Independent observation is supplied by the test application, not inferred
    from model text. This deliberately narrow gate accepts no unrelated tools.
    """
    if not source.execution_id:
        raise ValueError("missing_execution_identity")
    identities: set[str] = set()
    occurrences: dict[str, list[tuple[str, tuple[str, ...], str]]] = {}
    outputs: dict[str, dict[str, Any]] = {}

    def visit(node: RunResult, ancestors: tuple[str, ...]) -> None:
        identity = node.execution_id
        if not identity or identity in identities:
            raise ValueError("invalid_execution_identity")
        identities.add(identity)
        if not node.ok:
            raise ValueError("failed_execution")
        if ancestors and node.parent_execution_id != ancestors[-1]:
            raise ValueError("invalid_parent_reference")
        local: set[str] = set()
        for event in node.normalized()["tools"]:
            event_id = event["id"]
            if not event_id or event_id in local:
                raise ValueError("duplicate_or_missing_event_identity")
            local.add(event_id)
            if event["name"] != tool_name:
                raise ValueError("unexpected_tool")
            if not event["ok"] or event["error"] is not None:
                raise ValueError("failed_tool")
            if _canonical(event["input"]) != _canonical(expected_input):
                raise ValueError("input_mismatch")
            if _canonical(event["output"]) != _canonical(observed_output):
                raise ValueError("observation_mismatch")
            content = _canonical(event)
            occurrences.setdefault(event_id, []).append((identity, ancestors, content))
            outputs[event_id] = event["output"]
        for child in node.children:
            visit(child, (*ancestors, identity))

    visit(source, ())
    if len(occurrences) != 1:
        raise ValueError("expected_one_real_call")
    event_id, projections = next(iter(occurrences.items()))
    owner, ancestors, content = max(projections, key=lambda item: len(item[1]))
    for identity, _, projection in projections:
        if projection != content:
            raise ValueError("conflicting_event_projection")
        if identity != owner and identity not in ancestors:
            raise ValueError("shared_identity_between_siblings")
    return EvidenceSelection(
        source.execution_id, event_id, owner, _canonical(outputs[event_id])
    )
