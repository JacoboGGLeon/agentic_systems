from __future__ import annotations

from pathlib import Path

import agentic_systems as toolkit
from agentic_systems.compatibility import FRAMEWORK_NAMES, PROVIDER_NAMES
from agentic_systems.execution import CallableExecutable, is_executable


def test_callable_executable_and_plan_return_hierarchical_result():
    first = CallableExecutable(
        lambda value: {"value": value + 1},
        name="first",
    )
    second = CallableExecutable(
        lambda value: {"value": value["value"] * 2},
        name="second",
    )

    result = toolkit.SequentialPlan().execute([first, second], 2)

    assert result.ok is True
    assert result.data == {"value": 6}
    assert [child.meta["executable"] for child in result.children] == [
        "first",
        "second",
    ]
    assert list(result.walk()) == [result, *result.children]


def test_system_toolset_is_new_name_with_compatibility_registry():
    system = toolkit.system()
    current = system.toolset("math")
    legacy = system.toolkit("math")

    assert isinstance(current, toolkit.ToolSet)
    assert current is legacy
    assert system._toolsets is system._toolkits


def test_system_is_executable_and_compiles_registered_units():
    system = toolkit.system()
    system._agents.extend(
        [
            CallableExecutable(lambda value: {"value": value + 1}),
            CallableExecutable(lambda value: {"value": value["value"] * 2}),
        ]
    )

    result = system.run(2)

    assert is_executable(system)
    assert result.data == {"value": 6}
    assert len(result.children) == 2
    assert result.meta["compiled"] is True


def test_top_level_filesystem_skill_load_is_pure():
    path = (
        Path(__file__).resolve().parents[2]
        / "tutorials"
        / "skills"
        / "tutorial_api_inspection"
    )

    loaded = toolkit.load_skill(path)

    assert isinstance(loaded, toolkit.Skill)
    assert loaded.name == "tutorial_api_inspection"
    assert loaded.metadata["source"] == "filesystem_loader"


def test_provider_config_binds_to_runtime_without_becoming_framework():
    model_provider = toolkit.provider(
        "openai-runtime",
        model="gpt-test",
        endpoint="https://example.test/v1",
    )

    runtime = toolkit.runtime(provider=model_provider)

    assert runtime.provider == "openai-runtime"
    assert runtime.model_id == "gpt-test"
    assert runtime.metadata["model_provider"]["name"] == "openai-runtime"


def test_public_compatibility_matrix_covers_every_pair():
    cases = toolkit.compatibility_matrix()

    assert len(cases) == 20
    actual = {(case.provider, case.framework) for case in cases}
    expected = {
        (provider, framework)
        for provider in PROVIDER_NAMES
        for framework in FRAMEWORK_NAMES
    }
    assert actual == expected
    assert all(case.offline_certified for case in cases)


def test_parallel_plan_preserves_child_results():
    units = (
        CallableExecutable(lambda value: {"left": value}),
        CallableExecutable(lambda value: {"right": value}),
    )

    result = toolkit.ParallelPlan().execute(units, 3)

    assert result.data == {"results": [{"left": 3}, {"right": 3}]}
    assert len(result.children) == 2


def test_evaluator_accepts_compiled_system():
    unit = CallableExecutable(
        lambda value, **kwargs: {"value": value},
    )
    compiled = toolkit.CompiledSystem(units=(unit,))

    report = toolkit.eval().evaluate(compiled, [{"input": 7}])

    assert report.ok is True
    assert report.total == 1
