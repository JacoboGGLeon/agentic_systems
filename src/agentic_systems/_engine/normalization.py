"""Provider-neutral normalization of public model output."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re


_REASONING_TAGS = ("thinking", "think", "reasoning")
_OPENING = re.compile(
    r"^\ufeff?\s*<(?P<tag>thinking|think|reasoning)(?:\s[^>]*)?>", re.IGNORECASE
)
_JSON_FENCE = re.compile(
    r"\A[ \t\r\n]*```(?:json)?[ \t]*\r?\n(?P<body>.*?)\r?\n```[ \t\r\n]*\Z",
    re.DOTALL | re.IGNORECASE,
)


def _load_json_output(text: str | bytes | bytearray) -> object:
    """Decode one complete JSON document, optionally in one JSON/unlabelled fence.

    This removes formatting only. Prose, other fence languages, multiple blocks,
    incomplete documents and schema repair are never recovered here. Callers
    retain the original text and still validate the decoded value's contract.
    """
    match = _JSON_FENCE.fullmatch(text) if isinstance(text, str) else None
    return json.loads(match["body"] if match else text)


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


# Explicitly exported within the private engine for its provider/contract callers.
__all__ = ["PublicTextProjection", "contains_leading_reasoning", "project_public_text", "_load_json_output"]
