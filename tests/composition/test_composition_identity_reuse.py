import pytest

from agentic_systems.skills import Skill
from agentic_systems.system import AgenticSystem
from agentic_systems.tools import Tool


def _tool(name: str, value: int) -> Tool:
    def implementation() -> dict:
        return {"value": value}

    return Tool(name=name, function=implementation)


def test_same_skill_and_equal_mapping_values_are_idempotent_reuse() -> None:
    shared = Skill(name="shared", prompts={"instructions": "Same"})
    other = Skill(name="other", prompts={"instructions": "Same"})

    composed = Skill.compose(shared, shared, other, name="combined")
    reuse_events = [event for event in composed.composition()["events"] if event["decision"] == "reuse"]

    assert composed.instructions == "Same"
    assert {(event["kind"], event["identity"]) for event in reuse_events} == {
        ("skill", "shared"),
        ("prompt", "instructions"),
    }


def test_system_skill_identity_conflict_requires_explicit_precedence() -> None:
    system = AgenticSystem(strict=True)
    first = Skill(name="same", tools=[_tool("first", 1)])
    second = Skill(name="same", tools=[_tool("second", 2)])
    system.skill(first)

    with pytest.raises(ValueError, match="Skill identity 'same'.*No implicit override"):
        system.skill(second)
    assert system.skill(second, on_conflict="keep") is first
    assert system.skill(second, on_conflict="replace") is second
    assert system.runtime_skills == (second,)
    assert system.execute_tool("second").data == {"value": 2}
