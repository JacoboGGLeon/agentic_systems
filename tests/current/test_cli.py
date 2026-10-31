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


def test_cli_api_and_existing_destination(tmp_path, capsys):
    assert main(["api"]) == 0
    assert json.loads(capsys.readouterr().out)["public_api"] == toolkit.__all__
    target = tmp_path / "existing project"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("user work", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["new", str(target)])
    assert error.value.code == 2 and sentinel.read_text() == "user work"
    assert "existing projects" in capsys.readouterr().err
