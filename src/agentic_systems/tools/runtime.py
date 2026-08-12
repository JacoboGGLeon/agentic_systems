"""Runtime enforcement helpers owned by the Tool domain."""

from __future__ import annotations

import time
from typing import Any


def assert_dict_tool_output(tool_name: str, value: Any) -> dict[str, Any]:
    """Enforce the public contract that Tools return dictionaries."""

    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        fix = "return {'items': your_list}"
    elif isinstance(value, str):
        fix = "return {'text': your_text}"
    elif value is None:
        fix = "return {'ok': True}"
    elif hasattr(value, "model_dump"):
        fix = "return model.model_dump(mode='json')"
    else:
        fix = "return {'value': your_value}"
    raise TypeError(
        f"ToolContractError: Tool '{tool_name}' returned {type(value).__name__}. "
        "AgenticSystem tools must return dict. "
        f"Fix: {fix}."
    )


def now_ms() -> float:
    return time.perf_counter() * 1000.0


__all__ = ["assert_dict_tool_output", "now_ms"]
