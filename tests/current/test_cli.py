"""CLI reports its scope and does not overwrite user projects."""

import json

import pytest

import agentic_systems as toolkit
from agentic_systems.cli import main


def test_cli_dependencies_are_not_reported_as_services(capsys):
    assert main(["doctor"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["version"] == toolkit.__version__
    assert report["services_checked"] is False and report["inference_executed"] is False
    assert report["scope"] == "installed-dependencies-only"


def test_cli_api_and_removed_new_command(tmp_path, capsys):
    assert main(["api"]) == 0
    assert json.loads(capsys.readouterr().out)["public_api"] == toolkit.__all__
    target = tmp_path / "existing project"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("user work", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["new", str(target)])
    assert error.value.code == 2 and sentinel.read_text() == "user work"
    assert "invalid choice" in capsys.readouterr().err
    assert list(target.iterdir()) == [sentinel]


def test_help_exposes_only_supported_commands(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "{version,api,doctor,skill}" in help_text
    assert "new" not in help_text


def test_scaffolder_is_not_packaged():
    import importlib.util
    from importlib import resources
    assert importlib.util.find_spec('agentic_systems._scaffolding') is None
    assert not resources.files('agentic_systems').joinpath('_templates').is_dir()
