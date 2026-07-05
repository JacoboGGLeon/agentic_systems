from __future__ import annotations

import json


def test_cli_runtime_json_and_rich_output(capsys, monkeypatch):
    from agentic_systems import cli

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)

    assert cli.main(["runtime", "--provider", "python-direct", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_provider"] == "python-direct"
    assert payload["mode"] == "explicit"

    assert cli.main(["runtime", "--provider", "python-direct"]) == 0
    out = capsys.readouterr().out
    assert "Agentic Systems" in out
    assert "Runtime Resolution" in out
    assert "python-direct" in out


def test_cli_doctor_and_api_inventory(capsys):
    from agentic_systems import cli

    assert cli.main(["doctor", "--json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["package"] == "agentic-systems"
    assert "supported_engines" in doctor

    assert cli.main(["api", "--tier", "public", "--contains", "runtime", "--json"]) == 0
    api = json.loads(capsys.readouterr().out)
    assert api["tier"] == "public"
    assert any("runtime" in symbol.lower() for symbol in api["symbols"])


def test_cli_public_api_plain_json_and_runtime_safe_configuration(capsys, monkeypatch):
    from agentic_systems import cli

    class FakeRuntime:
        def describe(self):
            return {
                "selected_provider": "python-direct",
                "mode": "explicit",
                "preferred_provider": None,
                "fallback_provider": None,
                "reason": "test",
                "model": "local-python",
                "region": None,
                "scheduler": {"timeout_s": 1},
                "configuration": {"openai": {"api_key_configured": True}},
            }

    monkeypatch.setattr(cli, "runtime", lambda **kwargs: FakeRuntime())
    assert cli.main(["runtime", "--provider", "python-direct"]) == 0
    runtime_out = capsys.readouterr().out
    assert "Safe Configuration" in runtime_out
    assert "api_key_configured" in runtime_out

    assert cli.main(["public-api"]) == 0
    assert "Recommended API" in capsys.readouterr().out

    assert cli.main(["public-api", "--all", "--json"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)

    assert cli.main(["api", "--tier", "public", "--contains", "runtime"]) == 0
    api_out = capsys.readouterr().out
    assert "API Inventory" in api_out
    assert "runtime" in api_out
