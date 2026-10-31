import importlib.metadata
import json
from pathlib import Path

import pytest
import agentic_systems as toolkit


def test_metadata_surface_and_cli(capsys):
    from agentic_systems.cli import main
    assert toolkit.__version__ == "2.1.4.dev1"
    assert len(toolkit.__all__) == 21
    assert main(["version"]) == 0 and capsys.readouterr().out.strip() == "2.1.4.dev1"
    assert main(["api"]) == 0
    assert json.loads(capsys.readouterr().out)["public_api"] == toolkit.__all__
    assert main(["doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["inference_executed"] is False


def test_scaffolder_from_installed_resources_is_complete_and_no_overwrite(tmp_path):
    from agentic_systems._scaffolding import create_project
    project = create_project(tmp_path / "project")
    assert (project / "src/order_fulfillment/system.py").is_file()
    assert (project / "src/order_fulfillment/fixtures/cases.json").is_file()
    assert not (project / "src/unified_grammar").exists()
    assert f'agentic-systems=={toolkit.__version__}' in (project / "pyproject.toml").read_text()
    assert (project / "notebooks/01_order_challenge.ipynb").is_file()
    assert 'notebooks/01_order_challenge.ipynb' in (project / "execute_notebook.py").read_text()
    assert json.loads((project / "manifest.json").read_text())["validation"] == "not-run"
    with pytest.raises(FileExistsError):
        create_project(project)


def test_cli_new_uses_the_same_installed_scaffolder(tmp_path, capsys):
    from agentic_systems.cli import main
    destination = tmp_path / "cli-project"
    assert main(["new", str(destination)]) == 0
    assert capsys.readouterr().out.strip() == str(destination.resolve())
    assert (destination / "src/order_fulfillment/system.py").is_file()


def test_no_legacy_payload_methods_on_returns():
    result = toolkit.Agent("unit", toolkit.Action("step", lambda value: value)).run({"value": 1})
    for name in ("model_dump", "model_validate", "from_bedrock_runtime", "normalized", "native_result", "add_child"):
        assert not hasattr(result, name)
    config = toolkit.runtime(provider="python-runtime")
    for name in ("model_id", "region_name", "coerce", "describe", "to_dict", "scheduler", "allow_python_fallback"):
        assert not hasattr(config, name)


def test_pure_base_import_does_not_import_optional_sdks():
    # Import source graph is checked separately in a fresh Python at candidate collection.
    assert importlib.metadata.version("agentic-systems")
    package = Path(toolkit.__file__).parent
    assert all(p.name.startswith('_') or p.name == 'cli.py' for p in package.glob('*.py'))


def test_cli_module_entrypoint(monkeypatch, capsys):
    import runpy
    import sys
    monkeypatch.setattr(sys, "argv", ["agentic-systems", "version"])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_module("agentic_systems.cli", run_name="__main__")
    assert stopped.value.code == 0 and capsys.readouterr().out.strip() == "2.1.4.dev1"
