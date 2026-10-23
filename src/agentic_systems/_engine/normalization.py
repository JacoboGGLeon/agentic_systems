"""Provider-neutral normalization of public model output."""

from __future__ import annotations

from dataclasses import dataclass
import re


_REASONING_TAGS = ("thinking", "think", "reasoning")
_OPENING = re.compile(
    r"^\ufeff?\s*<(?P<tag>thinking|think|reasoning)(?:\s[^>]*)?>", re.IGNORECASE
)


@dataclass(frozen=True)
class PublicTextProjection:
    text: str
    reasoning_present: bool = False
    reasoning_format: str | None = None
    removed: bool = False


def project_public_text(value: object) -> PublicTextProjection:
    """Remove only one balanced, leading native-reasoning block.

    Tags inside prose or fenced code are left untouched.  Unbalanced blocks are
    also preserved because deleting uncertain content is less safe than
    exposing a provider formatting defect that the invariant gate will catch.
    """

    text = "" if value is None else str(value)
    opening = _OPENING.match(text)
    if opening is None:
        return PublicTextProjection(text=text)
    tag = opening.group("tag").lower()
    closing = re.compile(rf"</{re.escape(tag)}\s*>", re.IGNORECASE)
    match = closing.search(text, opening.end())
    if match is None:
        return PublicTextProjection(
            text=text,
            reasoning_present=True,
            reasoning_format=f"<{tag}>",
        )
    public = text[match.end() :].lstrip(" \t\r\n")
    return PublicTextProjection(
        text=public,
        reasoning_present=True,
        reasoning_format=f"<{tag}>",
        removed=True,
    )


def contains_leading_reasoning(value: object) -> bool:
    """Return whether text begins with a recognized reasoning tag."""

    return _OPENING.match("" if value is None else str(value)) is not None


__all__ = ["PublicTextProjection", "contains_leading_reasoning", "project_public_text"]
