import json

import pytest

from agentic_systems.providers.base import ToolRegistryRuntime
from agentic_systems.skills import Skill
from agentic_systems.system import AgenticSystem
from agentic_systems.tools import Tool


def _tool(name: str, value: int) -> Tool:
    def implementation() -> dict:
        return {"value": value}

    return Tool(name=name, function=implementation)


def test_tool_and_skill_identity_are_public_names() -> None:
    tool = _tool("lookup", 1)
    skill = Skill(name="research", tools=[tool])

    assert tool.identity == "lookup"
    assert tool.info()["identity"] == "lookup"
    assert skill.identity == "research"
    assert skill.info()["identity"] == "research"


def test_disjoint_skills_compose_as_a_non_executable_package() -> None:
    research = Skill(name="research", tools=[_tool("search", 1)], prompts={"research": "Search."})
    approval = Skill(name="approval", tools=[_tool("approve", 2)], contracts={"decision": "required"})

    composed = Skill.compose(research, approval, name="workflow")

    assert composed.tool_names == ("search", "approve")
    assert composed.prompts == {"research": "Search."}
    assert composed.contracts == {"decision": "required"}
    assert composed.composition()["sources"] == ["research", "approval"]
    assert not hasattr(composed, "run")


def test_shared_tool_definition_is_reused_and_inspectable() -> None:
    shared = _tool("lookup", 1)
    first = Skill(name="first", tools=[shared])
    second = Skill(name="second", tools=[shared])

    composed = Skill.compose(first, second, name="shared")
    tool_events = [event for event in composed.composition()["events"] if event["kind"] == "tool"]

    assert composed.tools == [shared]
    assert [event["decision"] for event in tool_events] == ["add", "reuse"]
    assert tool_events[-1]["selected_source"] == "first"


def test_skill_composition_rejects_implicit_tool_and_mapping_overrides() -> None:
    first = Skill(name="first", tools=[_tool("lookup", 1)], prompts={"instructions": "First"})
    second = Skill(name="second", tools=[_tool("lookup", 2)], prompts={"instructions": "Second"})

    with pytest.raises(ValueError, match="Tool identity 'lookup'.*No implicit override"):
        Skill.compose(first, second, name="ambiguous")

    prompt_only = Skill(name="prompt-only", prompts={"instructions": "Second"})
    with pytest.raises(ValueError, match="Prompt identity 'instructions'.*No implicit override"):
        Skill.compose(first, prompt_only, name="ambiguous-prompt")


@pytest.mark.parametrize(
    ("policy", "expected_value", "expected_instructions", "selected_source"),
    [
        ("keep", 1, "First", "first"),
        ("replace", 2, "Second", "second"),
    ],
)
def test_skill_precedence_is_explicit_and_deterministic(
    policy: str,
    expected_value: int,
    expected_instructions: str,
    selected_source: str,
) -> None:
    first = Skill(name="first", tools=[_tool("lookup", 1)], prompts={"instructions": "First"})
    second = Skill(name="second", tools=[_tool("lookup", 2)], prompts={"instructions": "Second"})

    composed = Skill.compose(first, second, name="resolved", on_conflict=policy)
    tool_event = next(
        event
        for event in composed.composition()["events"]
        if event["kind"] == "tool" and event["decision"] == policy
    )

    assert composed.tool("lookup").run().data == {"value": expected_value}
    assert composed.instructions == expected_instructions
    assert tool_event["selected_source"] == selected_source


def test_skill_source_identity_conflicts_require_a_policy() -> None:
    first = Skill(name="same", tools=[_tool("first", 1)])
    second = Skill(name="same", tools=[_tool("second", 2)])

    with pytest.raises(ValueError, match="Skill identity 'same'"):
        Skill.compose(first, second, name="ambiguous")

    kept = Skill.compose(first, second, name="kept", on_conflict="keep")
    replaced = Skill.compose(first, second, name="replaced", on_conflict="replace")
    assert kept.tool_names == ("first",)
    assert replaced.tool_names == ("second",)


def test_system_tool_registry_rejects_keeps_and_replaces_explicitly() -> None:
    system = AgenticSystem(strict=True)

    def first() -> dict:
        return {"value": 1}

    def second() -> dict:
        return {"value": 2}

    system.tool(first, name="lookup")
    with pytest.raises(ValueError, match="Tool identity 'lookup'.*No implicit override"):
        system.tool(second, name="lookup")
    system.tool(second, name="lookup", on_conflict="keep")
    assert system.execute_tool("lookup").data == {"value": 1}
    system.tool(second, name="lookup", on_conflict="replace")
    assert system.execute_tool("lookup").data == {"value": 2}

    entry = system.composition()["tools"][0]
    assert entry == {
        "identity": "lookup",
        "selected_source": "system.tool",
        "sources": ["system.tool"],
    }
    assert [event["decision"] for event in system.composition()["events"]] == [
        "add",
        "keep",
        "replace",
    ]


def test_system_skill_registration_is_idempotent_coherent_and_atomic() -> None:
    system = AgenticSystem(strict=True)
    first = Skill(name="first", tools=[_tool("lookup", 1)])
    second = Skill(name="second", tools=[_tool("lookup", 2)])

    assert system.skill(first) is first
    assert system.skill(first) is first
    with pytest.raises(ValueError, match="Tool identity 'lookup'"):
        system.skill(second)
    assert system.skill_names == ("first",)
    assert system.execute_tool("lookup").data == {"value": 1}

    assert system.skill(second, on_conflict="replace") is second
    assert system.skill_names == ("first", "second")
    assert system.execute_tool("lookup").data == {"value": 2}
    selected = next(item for item in system.composition()["tools"] if item["identity"] == "lookup")
    assert selected["selected_source"] == "skill:second"


def test_skill_keep_cannot_hide_a_different_registered_tool() -> None:
    system = AgenticSystem(strict=True)
    system.skill(Skill(name="first", tools=[_tool("lookup", 1)]))

    with pytest.raises(ValueError, match="would resolve to a different implementation"):
        system.skill(Skill(name="second", tools=[_tool("lookup", 2)]), on_conflict="keep")


def test_runtime_and_toolkit_registries_share_explicit_conflict_rules() -> None:
    runtime = ToolRegistryRuntime(model_id="python-runtime")

    def first() -> dict:
        return {"value": 1}

    def second() -> dict:
        return {"value": 2}

    runtime.tool(first, name="lookup")
    with pytest.raises(ValueError, match="No implicit override"):
        runtime.tool(second, name="lookup")
    runtime.tool(second, name="lookup", on_conflict="replace")
    assert runtime.execute_tool("lookup").data == {"value": 2}
    assert runtime.composition()["events"][-1]["decision"] == "replace"

    system = AgenticSystem(strict=True)
    toolkit = system.toolkit("crm")
    toolkit.tool(first, name="lookup")
    with pytest.raises(ValueError, match="crm.lookup"):
        toolkit.tool(second, name="lookup")
    toolkit.tool(second, name="lookup", on_conflict="replace")
    assert system.execute_tool("crm.lookup").data == {"value": 2}


def test_composition_reports_are_json_serializable_and_part_of_inspection() -> None:
    system = AgenticSystem(strict=True)
    skill = Skill(name="research", tools=[_tool("lookup", 1)])
    system.skill(skill)

    payload = system.inspect()

    assert payload["composition"] == system.composition()
    assert payload["composition"]["skills"][0]["identity"] == "research"
    assert json.loads(json.dumps(payload["composition"])) == payload["composition"]


def test_unknown_conflict_policy_is_rejected_clearly() -> None:
    skill = Skill(name="one")
    with pytest.raises(ValueError, match="Unknown conflict policy"):
        Skill.compose(skill, name="bad", on_conflict="last-wins")
    with pytest.raises(ValueError, match="requires at least one"):
        Skill.compose(name="empty")
