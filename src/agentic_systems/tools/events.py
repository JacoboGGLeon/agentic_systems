"""Observable events emitted by Tool execution."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolEvent(BaseModel):
    """Stable trace event for one Tool invocation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    error: dict[str, Any] | None = None
    duration_ms: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_runtime_record(cls, record: Any) -> "ToolEvent":
        """Convert a runtime tool-call record into a ToolEvent."""

        raw = (
            record.model_dump(mode="json")
            if hasattr(record, "model_dump")
            else dict(record)
        )
        tool_output = raw.get("tool_output") or {}
        data = tool_output.get("data") if isinstance(tool_output, dict) else None
        error = None
        if raw.get("ok") is False:
            error = data if isinstance(data, dict) else {"message": str(data)}
        return cls(
            id=str(raw.get("tool_use_id") or raw.get("id") or ""),
            name=str(raw.get("tool_name") or raw.get("name") or ""),
            input=raw.get("tool_input") or raw.get("input") or {},
            output=(
                tool_output
                if isinstance(tool_output, dict)
                else {"value": tool_output}
            ),
            ok=bool(raw.get("ok")),
            error=error,
            meta={"source": "bedrock_runtime", **(raw.get("meta") or {})},
        )


__all__ = ["ToolEvent"]
