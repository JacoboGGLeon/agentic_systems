from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib

import pytest
from pydantic import BaseModel

from agentic_systems.skills.skill import Skill
from agentic_systems.tools import tool as tool_decorator


class PayloadModel(BaseModel):
    value: int


@dataclass
class DataConfig:
    path: Path


tool_module = importlib.import_module("agentic_systems.tools.tool")


def test_skill_prompts_checks_json_like_and_errors():
    @tool_decorator(name="adder")
    def adder(a: int, b: int):
        return {"value": a + b}

    skill = Skill(
        name="math",
        version="1.2.3",
        description="fallback instructions",
        tools=[adder],
        prompts={"agent": "Use tools.", "user_prompt": "add"},
        metadata={
            "model": PayloadModel(value=1),
            "config": DataConfig(Path("x")),
            "cls": PayloadModel,
            "fn": adder.run,
        },
    )
    assert skill.instructions == "Use tools."
    assert skill.prompt() == "add"
    assert skill.prompt("missing", default="default") == "default"
    with pytest.raises(KeyError):
        skill.prompt("missing")
    assert skill.tool("adder") is adder
    with pytest.raises(KeyError):
        skill.tool("missing")
    assert len(skill) == 1
    assert list(skill)[0] is adder
    info = skill.info()
    assert info["metadata"]["model"] == {"value": 1}
    assert info["metadata"]["config"]["path"] == "x"
    assert info["metadata"]["cls"] == "PayloadModel"
    assert isinstance(info["metadata"]["fn"], str)

    duplicate = Skill(name="dup", tools=[adder, adder])
    assert duplicate.check().ok is False

    class BadTool:
        name = "bad"

        def check(self):
            from agentic_systems.contracts import ValidationResult

            result = ValidationResult()
            result.add("bad_tool", "broken", path="x", meta={"m": 1})
            return result

    checked = Skill(name="checked", tools=[])
    checked._tools = (BadTool(),)
    assert checked.check().issues[0].path == "tools[0].x"

    assert Skill(name="desc", description="desc").instructions == "desc"
    with pytest.raises(TypeError):
        Skill(name="bad", tools="not-tools")
    with pytest.raises(TypeError):
        Skill(name="bad", tools=[object()])
    with pytest.raises(TypeError):
        Skill(name="bad", prompts=[])
