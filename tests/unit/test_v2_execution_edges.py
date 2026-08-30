from __future__ import annotations

import argparse
import asyncio
from types import SimpleNamespace

import pytest

import agentic_systems as toolkit
import agentic_systems.cli as cli
import agentic_systems.compatibility as compatibility_module
from agentic_systems.api_contract import contract_entries
from agentic_systems.compatibility import CompatibilityCase, compatibility_report
from agentic_systems.core.provider import ModelProviderConfig
from agentic_systems.execution import (
    CallableExecutable,
    CompiledSystem,
    ParallelPlan,
    SequentialPlan,
    coerce_run_result,
)
from agentic_systems.factories import toolset
from agentic_systems.results import RunResult
from agentic_systems.skills.loader import SkillLoadError, load_skill_definition


def test_agent_pipeline_validates_and_compiles_public_stages():
    agent = toolkit.agent(
        name="pipeline_agent",
        runtime=toolkit.runtime(provider="python-runtime"),
    )
    stage = CallableExecutable(lambda value: value, name="stage")

    compiled = agent.pipeline(stage, name="pipeline")

    assert compiled.inspect() == {
        "name": "pipeline",
        "execution_plan": "sequential",
        "unit_count": 2,
    }
    with pytest.raises(TypeError, match="must implement run"):
        agent.pipeline(object())


def test_contract_introspection_covers_async_static_and_unknown_ids():
    async def async_export():
        return None

    class Example:
        @staticmethod
        def static() -> str:
            return "ok"

    namespace = SimpleNamespace(async_export=async_export, Example=Example)
    entries = contract_entries(namespace, ("async_export", "Example"))
    by_id = {entry.id: entry for entry in entries}

    assert by_id["async_export"].kind == "async-function"
    assert by_id["Example.static"].kind == "static-method"
    with pytest.raises(KeyError, match="Unknown public API"):
        toolkit.exercise_api("missing.contract.id")


def test_cli_error_contracts_and_human_rendering(capsys):
    with pytest.raises(ValueError, match="describe requires"):
        cli.main(["api", "describe"])
    with pytest.raises(KeyError, match="Unknown public API"):
        cli.main(["api", "describe", "missing.id"])
    with pytest.raises(ValueError, match="exercise requires"):
        cli.main(["api", "exercise"])

    assert cli.main(["api", "describe", "Agent.run"]) == 0
    assert "API Contract" in capsys.readouterr().out
    assert cli.main(["tool", "run"]) == 0
    assert "Tool Workflow" in capsys.readouterr().out

    with pytest.raises(ValueError, match="Unknown workflow"):
        cli._workflow_payload("unknown", argparse.Namespace())


def test_cli_matrix_distinguishes_not_ready_and_failed(monkeypatch):
    not_ready = CompatibilityCase(
        provider="openai-runtime",
        framework="native",
        offline_certified=True,
        ready=False,
        status="needs-configuration",
        reason="configure it",
    )
    ready = CompatibilityCase(
        provider="python-runtime",
        framework="native",
        offline_certified=True,
        ready=True,
        status="ready",
        reason="ready",
    )
    fake = SimpleNamespace(compatibility_matrix=lambda: (not_ready, ready))

    monkeypatch.setattr(
        cli,
        "_cli_agent",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    report = cli._matrix_workflow(fake, live=True)

    assert report["not_run"] == 1
    assert report["failed"] == 1
    assert report["results"][0]["execution_reason"] == "configure it"
    assert report["results"][1]["error"]["type"] == "RuntimeError"


def test_compatibility_report_and_missing_dependency(monkeypatch):
    report = compatibility_report()
    assert report["combination_count"] == 20

    monkeypatch.setattr(
        compatibility_module.importlib.util, "find_spec", lambda _name: None
    )
    missing = toolkit.compatibility_matrix()
    external_frameworks = [case for case in missing if case.framework != "native"]

    assert external_frameworks
    assert all(case.status == "missing-dependency" for case in external_frameworks)


def test_compatibility_matrix_reports_unconfigured_provider(monkeypatch):
    monkeypatch.setattr(compatibility_module, "_load_dotenv", lambda: None)
    monkeypatch.setattr(compatibility_module, "_openai_signal_present", lambda: False)
    monkeypatch.setattr(
        compatibility_module.importlib.util, "find_spec", lambda _name: object()
    )

    cases = toolkit.compatibility_matrix()
    openai_cases = [case for case in cases if case.provider == "openai-runtime"]

    assert openai_cases
    assert all(case.status == "needs-configuration" for case in openai_cases)
    assert all(case.ready is False for case in openai_cases)


def test_model_provider_identity_and_toolset_owner_validation():
    config = ModelProviderConfig("python-runtime")
    assert config.identity == "python-runtime"
    owner = toolkit.system(runtime=toolkit.runtime(provider="python-runtime"))
    assert toolset(owner, "owned") is owner.toolset("owned")
    with pytest.raises(TypeError, match="AgenticSystem owner"):
        toolset(object(), "invalid")


def test_execution_plan_paths_and_async_compiled_system():
    assert coerce_run_result(None).ok is True
    assert coerce_run_result("text").text == "text"

    stopped = SequentialPlan().execute(
        [
            CallableExecutable(lambda _value: RunResult(ok=False)),
            CallableExecutable(lambda _value: {"unreachable": True}),
        ],
        "input",
    )
    assert len(stopped.children) == 1

    selected = SequentialPlan(input_selector=lambda child: child.final).execute(
        [CallableExecutable(lambda _value: {"selected": True})],
        "input",
    )
    assert selected.ok is True

    seen: list[object] = []
    text_plan = SequentialPlan().execute(
        [
            CallableExecutable(lambda _value: RunResult(text="next")),
            CallableExecutable(lambda value: seen.append(value) or {"ok": True}),
        ]
    )
    assert text_plan.ok is True
    assert seen == ["next"]

    seen.clear()
    final_plan = SequentialPlan().execute(
        [
            CallableExecutable(lambda _value: RunResult(final={"next": True})),
            CallableExecutable(lambda value: seen.append(value) or {"ok": True}),
        ]
    )
    assert final_plan.ok is True
    assert seen == [{"next": True}]

    parallel = ParallelPlan().execute(
        [
            CallableExecutable(lambda _value: RunResult(usage={"tokens": 2})),
            CallableExecutable(
                lambda _value: RunResult(usage={"tokens": 3, "cached": True})
            ),
        ]
    )
    assert parallel.usage == {"tokens": 5}

    compiled = CompiledSystem(
        units=(CallableExecutable(lambda value: {"value": value}),),
        name="async-system",
    )
    result = asyncio.run(compiled.arun("ok"))
    assert result.data == {"value": "ok"}
    assert compiled.inspect()["unit_count"] == 1

    entrypoint = CompiledSystem(
        units=(CallableExecutable(lambda value: {"value": value}),),
        entrypoint="orchestrator",
    )
    assert entrypoint.inspect()["entrypoint"] == "orchestrator"


def test_result_children_validate_and_inherit_parent_execution_id():
    parent = RunResult(execution_id="parent")
    child = RunResult()

    assert parent.add_child(child) is parent
    assert child.parent_execution_id == "parent"
    assert list(parent.walk()) == [parent, child]
    with pytest.raises(TypeError, match="Expected RunResult"):
        parent.add_child(object())


def test_filesystem_skill_loader_errors_and_build_alias(tmp_path):
    with pytest.raises(SkillLoadError, match="does not exist"):
        load_skill_definition(tmp_path / "missing")

    missing_markdown = tmp_path / "missing_markdown"
    missing_markdown.mkdir()
    with pytest.raises(SkillLoadError, match="missing SKILL.md"):
        load_skill_definition(missing_markdown)

    missing_python = tmp_path / "missing_python"
    missing_python.mkdir()
    (missing_python / "SKILL.md").write_text("# Skill", encoding="utf-8")
    with pytest.raises(SkillLoadError, match="missing skill.py"):
        load_skill_definition(missing_python)

    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "SKILL.md").write_text("# Skill", encoding="utf-8")
    (invalid / "skill.py").write_text(
        "def build_skill():\n    return 1\n",
        encoding="utf-8",
    )
    with pytest.raises(SkillLoadError, match="must return a Skill"):
        load_skill_definition(invalid)

    no_builder = tmp_path / "no_builder"
    no_builder.mkdir()
    (no_builder / "SKILL.md").write_text("# Skill", encoding="utf-8")
    (no_builder / "skill.py").write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(SkillLoadError, match="must expose build_skill"):
        load_skill_definition(no_builder)

    alias = tmp_path / "alias"
    alias.mkdir()
    (alias / "SKILL.md").write_text("# Skill", encoding="utf-8")
    (alias / "skill.py").write_text(
        "import agentic_systems as toolkit\n"
        "def build():\n"
        "    return toolkit.skill(name='alias')\n",
        encoding="utf-8",
    )
    loaded = load_skill_definition(alias)
    assert loaded.name == "alias"


def test_system_add_deduplicates_and_async_run():
    current = toolkit.system(runtime=toolkit.runtime(provider="python-runtime"))
    unit = CallableExecutable(lambda value: {"value": value})

    assert current.add(unit) is unit
    assert current.add(unit) is unit
    assert len(current.agents) == 1
    result = asyncio.run(current.arun("ok"))
    assert result.data == {"value": "ok"}

    with pytest.raises(TypeError, match="expects an object with run"):
        current.add(object())
