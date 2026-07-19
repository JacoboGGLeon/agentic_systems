"""Internal composition rules shared by Tool and Skill registries."""

from __future__ import annotations

from typing import Any, Literal


ConflictPolicy = Literal["error", "keep", "replace"]
CONFLICT_POLICIES = ("error", "keep", "replace")


def normalize_conflict_policy(value: str) -> ConflictPolicy:
    """Validate and normalize an explicit composition conflict policy."""

    policy = str(value or "error").strip().lower()
    if policy not in CONFLICT_POLICIES:
        raise ValueError(
            f"Unknown conflict policy {value!r}. Expected one of: {list(CONFLICT_POLICIES)}."
        )
    return policy  # type: ignore[return-value]


def conflict_message(kind: str, name: str, existing_source: str, incoming_source: str) -> str:
    """Return one actionable collision message for every composition surface."""

    return (
        f"{kind} identity {name!r} is already registered from {existing_source!r}; "
        f"incoming source is {incoming_source!r}. No implicit override was applied. "
        "Pass on_conflict='keep' or on_conflict='replace' explicitly."
    )


def same_tool_definition(left: Any, right: Any) -> bool:
    """Return whether two Tool-like objects describe the same concrete capability."""

    return left is right or (
        left.identity == right.identity
        and left.function is right.function
        and left.description == right.description
        and left.input_schema is right.input_schema
        and left.output_schema is right.output_schema
        and left.strict == right.strict
        and left.metadata == right.metadata
    )


__all__ = ["ConflictPolicy", "normalize_conflict_policy"]
