from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import agentic_systems as toolkit

from agentic_systems_studio import (
    SYSTEM_SPECS,
    StudioConfig,
    StudioStore,
    build_system,
    compose_systems,
    create_application,
    scaffold_application,
)
from agentic_systems_studio.components import (
    AGENT_ASSETS,
    ENVIRONMENT_ASSETS,
    EVAL_ASSETS,
    SKILL_ASSETS,
    TOOL_ASSETS,
)
from agentic_systems_studio.operators import OPERATOR_TOOLS


def test_catalog_has_ten_distinct_varied_systems():
    assert len(SYSTEM_SPECS) == 10
    assert len({spec.id for spec in SYSTEM_SPECS}) == 10
    assert {spec.size for spec in SYSTEM_SPECS} == {"small", "medium", "large"}
    assert {len(spec.stages) for spec in SYSTEM_SPECS} >= {2, 3, 4, 5}


def test_every_system_combines_operator_and_reasoning_units():
    for spec in SYSTEM_SPECS:
        kinds = {stage.kind for stage in spec.stages}
        assert "operator" in kinds
        assert kinds & {"reasoner", "reviewer"}
        assert spec.runtime_skill
        assert len(spec.assets) >= 8


def test_component_tabs_have_real_inventory():
    assert len(TOOL_ASSETS) >= 10
    assert len(SKILL_ASSETS) == 10
    assert len(AGENT_ASSETS) == sum(len(spec.stages) for spec in SYSTEM_SPECS)
    assert len(ENVIRONMENT_ASSETS) >= 5
    assert len(EVAL_ASSETS) >= 5


def test_deterministic_operators_execute_for_every_system():
    for spec in SYSTEM_SPECS:
        result = OPERATOR_TOOLS[spec.id].run({"text": spec.sample_input})
        assert result.ok, (spec.id, result)
        assert result.data


def test_data_quality_operator_extracts_csv_from_natural_language_prompt():
    result = OPERATOR_TOOLS["data-quality"].run(
        {
            "text": "Inspect this CSV and propose a remediation:\n"
            "id,name,amount\n1,Ana,10\n2,,20\n2,,20"
        }
    )
    assert result.ok
    assert result.data["row_count"] == 3
    assert result.data["columns"] == ["id", "name", "amount"]
    assert result.data["null_counts"]["name"] == 2
    assert result.data["duplicate_rows"] == 1


@pytest.mark.parametrize("spec", SYSTEM_SPECS, ids=lambda spec: spec.id)
def test_catalog_builds_exact_public_system(spec):
    studio_system = build_system(
        spec.id,
        StudioConfig(provider="openai-runtime", framework="native"),
    )
    inspection = studio_system.inspect()
    assert inspection["compiled"]["unit_count"] == len(spec.stages)
    assert inspection["catalog"]["id"] == spec.id
    assert not inspection.get("errors")
    diagram = studio_system.mermaid()
    for index, stage in enumerate(spec.stages):
        assert f"stage_{index}_{stage.id.replace('-', '_')}" in diagram
        assert stage.name in diagram


def test_system_of_systems_is_hierarchical_and_uses_public_plans():
    sequential = compose_systems(
        ("data-quality", "decision-intelligence"),
        StudioConfig(provider="openai-runtime"),
        mode="sequential",
    )
    parallel = compose_systems(
        ("prompt-security", "quantitative-analysis"),
        StudioConfig(provider="openai-runtime"),
        mode="parallel",
    )
    assert sequential.compiled.inspect() == {
        "name": "studio-sequential-composition",
        "execution_plan": "sequential",
        "unit_count": 2,
    }
    assert parallel.compiled.inspect() == {
        "name": "studio-parallel-composition",
        "execution_plan": "parallel",
        "unit_count": 2,
    }
    assert "data-quality" in sequential.mermaid()
    assert "decision-intelligence" in sequential.mermaid()


def test_sqlite_inventory_matches_catalog(tmp_path: Path):
    store = StudioStore(tmp_path / "studio.db")
    assert store.inventory() == {
        "systems": 10,
        "stages": sum(len(spec.stages) for spec in SYSTEM_SPECS),
        "assets": sum(len(set(spec.assets)) for spec in SYSTEM_SPECS),
        "runs": 0,
        "compositions": 0,
    }
    with sqlite3.connect(store.path) as connection:
        manifest = json.loads(
            connection.execute(
                "SELECT manifest_json FROM systems WHERE id = ?",
                ("agentic-systems-creator",),
            ).fetchone()[0]
        )
    assert manifest["size"] == "large"
    assert len(manifest["stages"]) == 5


def test_scaffolder_generates_complete_non_destructive_application(tmp_path: Path):
    target = tmp_path / "reference"
    report = scaffold_application(
        target,
        name="Reference Application",
        system_id="incident-response",
    )
    relative = {path.relative_to(target).as_posix() for path in report.files}
    assert {
        "manifest.json",
        "assets/system.mmd",
        "data/app.db",
        "notebooks/00_walkthrough.ipynb",
        "skills/codex-agentic-application/SKILL.md",
        "tests/test_contract.py",
        "tests/test_execution.py",
        "src/reference_application/tools.py",
        "src/reference_application/skills.py",
        "src/reference_application/agents.py",
        "src/reference_application/settings.py",
    } <= relative
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["id"] == "incident-response"
    assert set(manifest["assets"]) == relative
    assert manifest["execution"]["plan"] == "sequential"
    assert manifest["agentic_systems_version"] == toolkit.__version__
    assert manifest["runtime_policy"]["default_provider"] == "auto"
    assert manifest["runtime_policy"]["default_framework"] == "native"
    assert "agentic-systems" not in manifest["runtime_policy"]["frameworks"]
    assert "python-runtime" not in manifest["runtime_policy"]["reasoning_providers"]
    settings = (target / "src/reference_application/settings.py").read_text(
        encoding="utf-8"
    )
    assert 'os.getenv("AGENTIC_SYSTEMS_PROVIDER", "auto")' in settings
    assert 'os.getenv("AGENTIC_SYSTEMS_FRAMEWORK", "native")' in settings
    env_example = (target / ".env.example").read_text(encoding="utf-8")
    assert "AGENTIC_SYSTEMS_PROVIDER=auto" in env_example
    assert "AGENTIC_SYSTEMS_FRAMEWORK=native" in env_example
    assert "AGENTIC_PROVIDER=" not in env_example
    source = (target / "src/reference_application/tools.py").read_text(encoding="utf-8")
    for stage in manifest["stages"]:
        assert f"def {stage['tool_key']}" in source
    validation = report.validate()
    assert validation["ok"] is True
    assert all(validation["checks"].values())
    with sqlite3.connect(target / "data/app.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM stages").fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM tools").fetchone()[0] == 3
    with pytest.raises(FileExistsError):
        scaffold_application(
            target,
            name="Reference Application",
            system_id="incident-response",
        )


def test_scaffold_validation_rejects_a_missing_declared_tool(tmp_path: Path):
    target = tmp_path / "tampered"
    report = scaffold_application(
        target,
        name="Tampered Application",
        system_id="prompt-security",
    )
    tools_path = target / "src/tampered_application/tools.py"
    source = tools_path.read_text(encoding="utf-8")
    tools_path.write_text(
        source.replace("def scan_prompt_security", "def removed_prompt_security"),
        encoding="utf-8",
    )
    validation = report.validate()
    assert validation["ok"] is False
    assert validation["checks"]["manifest_tools_resolve"] is False


def test_creator_materializes_validated_portable_application(
    monkeypatch, tmp_path: Path
):
    class FakeCreator:
        def run(self, request, **_kwargs):
            return toolkit.RunResult(
                text="Blueprint ready.",
                data={"request": request},
                engine="openai-runtime",
                model="test-model",
                mode="create",
            )

    monkeypatch.setattr(
        "agentic_systems_studio.creator.build_system",
        lambda *_args, **_kwargs: FakeCreator(),
    )
    result = create_application(
        "Create an incident response system.",
        tmp_path / "created",
        name="Created Incident System",
        template_system_id="incident-response",
    )

    assert result.ok is True
    assert result.mode == "create"
    assert result.data["generated"] is True
    assert len(result.children) == 2
    artifact = result.data["artifact"]
    assert artifact["validation"]["ok"] is True
    assert artifact["file_count"] >= 10
    assert Path(artifact["root"], "manifest.json").is_file()
    assert "Agentic System generated successfully" in result.text


def test_python_runtime_is_rejected_for_reasoning_catalog():
    with pytest.raises(ValueError, match="reasoning agents"):
        build_system(
            "data-quality",
            StudioConfig(provider="python-runtime"),
        )
