import json
from pathlib import Path
import runpy
import sys

import pytest
import agentic_systems as t


def test_cli_reports_the_current_surface(capsys):
    from agentic_systems.cli import main
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == t.__version__
    assert main(["api"]) == 0
    assert json.loads(capsys.readouterr().out)["public_api"] == t.__all__
    assert main(["doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["inference_executed"] is False


def test_current_scaffolder_generates_only_langgraph_and_runs_offline(tmp_path):
    from agentic_systems._scaffolding import create_project
    project = create_project(tmp_path / "application")
    assert f'agentic-systems=={t.__version__}' in (project / "pyproject.toml").read_text(encoding="utf-8")
    notebook = json.loads((project / "notebooks/01_order_challenge.ipynb").read_text(encoding="utf-8"))
    code = "".join("".join(c["source"]) for c in notebook["cells"])
    assert "for backend" not in code and "demonstrate()" in code
    assert "from order_fulfillment import demonstrate" not in code
    assert "toolkit.Agent(" in code and "toolkit.System(" in code
    assert "toolkit.Environment(" in code and "toolkit.Eval(" in code
    for path in project.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "toolkit.Sequence" not in source and "toolkit.Parallel" not in source and "toolkit.StateGraph" not in source
    try:
        runpy.run_path(str(project / "app.py"), run_name="__main__")
        report = json.loads((project / "evidence/run-results.json").read_text(encoding="utf-8"))
        assert report["output"]["refund"] == 120
        assert report["output"]["status"] == "approved"
    finally:
        sys.path[:] = [path for path in sys.path if path != str(project / "src")]
        for name in list(sys.modules):
            if name == "order_fulfillment" or name.startswith("order_fulfillment."):
                del sys.modules[name]
    assert json.loads((project / "manifest.json").read_text())["validation"] == "not-run"
    with pytest.raises(FileExistsError):
        create_project(project)


def test_cli_new_preserves_existing_files(tmp_path, capsys):
    from agentic_systems.cli import main
    destination = tmp_path / "project"
    assert main(["new", str(destination)]) == 0
    assert Path(capsys.readouterr().out.strip()) == destination
    assert (destination / "src/order_fulfillment/application.py").is_file()
    with pytest.raises(SystemExit) as rejected:
        main(["new", str(destination)])
    assert rejected.value.code == 2
    assert "existing projects" in capsys.readouterr().err
