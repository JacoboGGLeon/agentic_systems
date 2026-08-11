from __future__ import annotations

import json

import agentic_systems.cli as cli_module


def test_cli_plain_and_json_paths(monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "_load_dotenv", lambda: True)
    monkeypatch.setattr(cli_module, "_optional_dependency", lambda name: name != "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("AWS_REGION", "us-test-1")
    monkeypatch.setenv("AWS_PROFILE", "profile")

    assert cli_module.main(["version"]) == 0
    assert cli_module.__version__ in capsys.readouterr().out

    assert cli_module.main(["doctor"]) == 0
    doctor_plain = capsys.readouterr().out
    assert "Agentic Systems" in doctor_plain
    assert "OPENAI_API_KEY: set" in doctor_plain
    assert "openai: missing" in doctor_plain

    assert cli_module.main(["doctor", "--json"]) == 0
    doctor_json = json.loads(capsys.readouterr().out)
    assert doctor_json["dotenv_loaded"] is True
    assert doctor_json["environment"]["has_aws_profile"] is True

    class FakeRuntime:
        def describe(self):
            return {"selected_provider": "python-runtime", "mode": "explicit"}

    monkeypatch.setattr(cli_module, "runtime", lambda **kwargs: FakeRuntime())
    assert cli_module.main(["runtime", "--provider", "python-runtime"]) == 0
    runtime_plain = capsys.readouterr().out
    assert "Runtime Resolution" in runtime_plain
    assert "python-runtime" in runtime_plain
    assert cli_module.main(["runtime", "--provider", "python-runtime", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "explicit"

    assert cli_module.main(["public-api"]) == 0
    assert capsys.readouterr().out.strip()
    assert cli_module.main(["public-api", "--all", "--json"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)

    assert cli_module.main(["api", "--tier", "public", "--contains", "runtime"]) == 0
    api_plain = capsys.readouterr().out
    assert "tier: public" in api_plain
    assert "runtime" in api_plain.lower()
    assert cli_module.main(["api", "--tier", "recommended", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tier"] == "recommended"
