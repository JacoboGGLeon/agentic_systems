from __future__ import annotations

import json
import inspect
from pathlib import Path
import re
import shlex
import subprocess
import sys

import pytest

import agentic_systems as toolkit
from agentic_systems.api import PUBLIC_API
from agentic_systems.cli import build_parser, main


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DOC = ROOT / "docs" / "API_CONTRACT.md"
CONTRACT_NOTEBOOK = ROOT / "tutorials" / "api" / "14_api_contract_matrix.ipynb"
MANIFEST = toolkit.api_contract()
SHARED_SCENARIOS = tuple(MANIFEST["scenarios"])
SCENARIO_IDS = tuple(MANIFEST["scenario_ids"])
CONTRACT_IDS = tuple(MANIFEST["ids"])


def test_source_api_and_manifest_are_the_same_surface():
    export_ids = tuple(
        entry["id"]
        for entry in MANIFEST["entries"]
        if entry["member"] is None
    )

    assert tuple(toolkit.__all__) == PUBLIC_API
    assert export_ids == PUBLIC_API
    assert MANIFEST["export_count"] == len(PUBLIC_API)
    assert MANIFEST["entry_count"] == len(CONTRACT_IDS)
    assert len(CONTRACT_IDS) == len(set(CONTRACT_IDS))

def test_manifest_contains_every_library_owned_visible_class_member():
    contracted = set(CONTRACT_IDS)
    missing = []

    for export in PUBLIC_API:
        owner = getattr(toolkit, export)
        if not inspect.isclass(owner):
            continue

        for member in dir(owner):
            if member.startswith("_") or member == "model_config":
                continue
            defining_owner = next(
                (
                    base
                    for base in owner.__mro__
                    if member in base.__dict__
                    and getattr(base, "__module__", "").startswith("agentic_systems")
                ),
                None,
            )
            if defining_owner is None:
                continue
            value = inspect.getattr_static(defining_owner, member)
            if inspect.ismodule(value) or inspect.isclass(value):
                continue
            identifier = f"{export}.{member}"
            if identifier not in contracted:
                missing.append(identifier)

    assert missing == []
    assert {
        "ToolSet.add",
        "ToolSet.ref",
        "ToolSet.tool",
        "ToolSet.tool_names",
        "AsyncExecutable.run",
        "GraphApp.graph_kind",
        "GraphApp.framework",
        "AgenticGraph.graph_kind",
        "AgenticGraph.framework",
    } <= contracted
    entries = {entry["id"]: entry for entry in MANIFEST["entries"]}
    assert entries["ToolSet.add"]["source"] == (
        "agentic_systems.tools.toolkit:Toolkit.add"
    )
    assert entries["AsyncExecutable.run"]["source"] == (
        "agentic_systems.execution:Executable.run"
    )


def test_shared_scenario_registry_is_complete_and_resolvable():
    assert MANIFEST["scenario_count"] == 10
    assert SCENARIO_IDS == (
        "runtime",
        "tool",
        "skill",
        "agent",
        "system",
        "graph",
        "environment",
        "eval",
        "matrix",
        "api_contract",
    )
    assert len(SCENARIO_IDS) == len(set(SCENARIO_IDS))

    for scenario in SHARED_SCENARIOS:
        assert scenario["id"] in SCENARIO_IDS
        assert scenario["api_ids"]
        assert set(scenario["api_ids"]) <= set(CONTRACT_IDS)
        assert scenario["cli"].startswith("agentic-systems ")
        argv = shlex.split(scenario["cli"])[1:]
        parsed = build_parser().parse_args(argv)
        assert callable(parsed.func)
        assert scenario["notebooks"]
        assert all((ROOT / "tutorials" / path).exists() for path in scenario["notebooks"])
        pytest_path, selector = scenario["pytest"].split("::", 1)
        assert (ROOT / pytest_path).exists()
        assert selector == (
            f"test_shared_scenario_cli_executes[{scenario['id']}]"
        )



@pytest.mark.parametrize("scenario", SHARED_SCENARIOS, ids=SCENARIO_IDS)
def test_shared_scenario_cli_executes(scenario, capsys):
    argv = shlex.split(scenario["cli"])[1:]
    assert main(argv) == 0
    payload = json.loads(capsys.readouterr().out)

    if scenario["id"] == "runtime":
        assert payload["selected_provider"] == "python-runtime"
        assert payload["mode"] == "explicit"
    elif scenario["id"] == "api_contract":
        assert payload["ok"] is True
        assert payload["count"] == len(CONTRACT_IDS)
        assert tuple(item["id"] for item in payload["results"]) == CONTRACT_IDS
    else:
        assert payload["scenario"] == scenario["id"]
        assert payload["scenario_api_ids"] == scenario["api_ids"]


@pytest.mark.parametrize("identifier", CONTRACT_IDS, ids=CONTRACT_IDS)
def test_every_contract_id_has_pytest_evidence(identifier: str):
    evidence = toolkit.exercise_api(identifier)

    assert evidence["ok"] is True
    assert evidence["count"] == 1
    assert evidence["results"][0]["id"] == identifier


def test_documentation_and_reference_notebook_have_the_same_ids():
    contract_text = CONTRACT_DOC.read_text("utf-8")
    documented = tuple(
        re.findall(r"^## `([A-Za-z_][A-Za-z0-9_.]*)`$", contract_text, re.M)
    )
    notebook = json.loads(CONTRACT_NOTEBOOK.read_text("utf-8"))
    namespace: dict[str, object] = {}
    inventory_cell = next(
        cell
        for cell in notebook["cells"]
        if "EXPECTED_API_IDS" in "".join(cell.get("source", []))
    )
    exec("".join(inventory_cell["source"]), {}, namespace)

    assert documented == CONTRACT_IDS
    assert tuple(namespace["EXPECTED_API_IDS"]) == CONTRACT_IDS
    assert tuple(namespace["EXPECTED_SCENARIO_IDS"]) == SCENARIO_IDS
    assert tuple(namespace["EXPECTED_SCENARIOS"]) == SHARED_SCENARIOS
    assert namespace["EXPECTED_CHECKSUM"] == MANIFEST["checksum"]
    for scenario_id in SCENARIO_IDS:
        assert f"| `{scenario_id}` |" in contract_text


def test_cli_resolves_and_exercises_the_complete_registry(capsys):
    assert main(["api", "list", "--tier", "public", "--json"]) == 0
    public_inventory = json.loads(capsys.readouterr().out)
    assert tuple(public_inventory["ids"]) == CONTRACT_IDS
    assert public_inventory["count"] == len(CONTRACT_IDS)

    tier_ids = {}
    assert {entry["tier"] for entry in MANIFEST["entries"]} == {
        "recommended",
        "advanced",
    }

    for tier in ("recommended", "advanced"):
        assert main(["api", "list", "--tier", tier, "--json"]) == 0
        inventory = json.loads(capsys.readouterr().out)
        tier_ids[tier] = set(inventory["ids"])
        assert inventory["count"] == len(tier_ids[tier])
        expected = tuple(
            entry["id"] for entry in MANIFEST["entries"] if entry["tier"] == tier
        )
        assert tuple(inventory["ids"]) == expected

    assert tier_ids["recommended"].isdisjoint(tier_ids["advanced"])
    assert tier_ids["recommended"] | tier_ids["advanced"] == set(CONTRACT_IDS)

    for identifier in CONTRACT_IDS:
        assert main(["api", "describe", identifier, "--json"]) == 0
        described = json.loads(capsys.readouterr().out)
        assert described["id"] == identifier

        assert main(["api", "exercise", identifier, "--json"]) == 0
        exercised = json.loads(capsys.readouterr().out)
        assert exercised["ok"] is True
        assert exercised["results"][0]["id"] == identifier

    assert main(["api", "exercise", "--all", "--json"]) == 0
    all_evidence = json.loads(capsys.readouterr().out)
    assert tuple(item["id"] for item in all_evidence["results"]) == CONTRACT_IDS


def test_generated_contract_is_reproducible_across_processes():
    command = [sys.executable, "scripts/generate_api_contract.py", "--check"]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
