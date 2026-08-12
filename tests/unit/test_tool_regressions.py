import os

import pytest
from pydantic import BaseModel

from agentic_systems import (
    AgenticSystem,
)
from agentic_systems.tools.compat import (
    Toolkit,
    assert_dict_tool_output,
    expand_tool_inputs,
    now_ms,
)


def build_system(strict=True, defaults=None):

    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(
        model="demo-model", region="us-east-1", strict=strict, defaults=defaults
    )


def test_tools_and_toolkit_public_helpers():
    class Model(BaseModel):
        value: int

    for value, fix in [
        ([1], "items"),
        ("x", "text"),
        (None, "ok"),
        (Model(value=1), "model_dump"),
        (3.14, "value"),
    ]:
        with pytest.raises(TypeError, match=fix):
            assert_dict_tool_output("sample", value)

    system = build_system(strict=False)
    with pytest.raises(ValueError, match="non-empty"):
        Toolkit(system, " ")

    toolkit = system.toolkit("demo")

    @toolkit.tool
    def one() -> list:
        """Strict false allows runtime values through."""
        return [1]

    def dotted() -> dict:
        """Already namespaced."""
        return {"ok": True}

    toolkit.add(dotted, name="external.dotted")
    assert len(toolkit) == 2
    assert list(iter(toolkit)) == ["demo.one", "external.dotted"]
    assert toolkit.ref().name == "demo"
    assert expand_tool_inputs(None) == ()
    assert expand_tool_inputs(toolkit) == toolkit.tool_names
    assert expand_tool_inputs("demo.one") == ("demo.one",)
    assert expand_tool_inputs([toolkit, "demo.one"]).count("demo.one") == 2
    with pytest.raises(TypeError, match="Unsupported tools"):
        expand_tool_inputs(123)
    assert now_ms() > 0
