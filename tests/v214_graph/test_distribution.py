import json

import agentic_systems as t


def test_cli_reports_the_current_surface(capsys):
    from agentic_systems.cli import main
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == t.__version__
    assert main(["api"]) == 0
    assert json.loads(capsys.readouterr().out)["public_api"] == t.__all__
    assert main(["doctor"]) == 0
    assert json.loads(capsys.readouterr().out)["inference_executed"] is False
