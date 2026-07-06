from __future__ import annotations

import json


def test_cli_runtime_json_and_rich_output(capsys, monkeypatch):
    from agentic_systems import cli

    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)

    assert cli.main(["runtime", "--provider", "python-runtime", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_provider"] == "python-runtime"
    assert payload["mode"] == "explicit"

    assert cli.main(["runtime", "--provider", "python-runtime"]) == 0
    out = capsys.readouterr().out
    assert "Agentic Systems" in out
    assert "Runtime Resolution" in out
    assert "python-runtime" in out


def test_cli_doctor_and_api_inventory(capsys):
    from agentic_systems import cli

    assert cli.main(["doctor", "--json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["package"] == "agentic-systems"
    assert "supported_engines" in doctor
    assert "vllm-runtime" in doctor["supported_engines"]
    assert "has_vllm_base_url" in doctor["environment"]

    assert cli.main(["api", "--tier", "public", "--contains", "runtime", "--json"]) == 0
    api = json.loads(capsys.readouterr().out)
    assert api["tier"] == "public"
    assert any("runtime" in symbol.lower() for symbol in api["symbols"])


def test_cli_public_api_plain_json_and_runtime_safe_configuration(capsys, monkeypatch):
    from agentic_systems import cli

    class FakeRuntime:
        def describe(self):
            return {
                "selected_provider": "python-runtime",
                "mode": "explicit",
                "preferred_provider": None,
                "fallback_provider": None,
                "reason": "test",
                "model": "python-runtime",
                "region": None,
                "scheduler": {"timeout_s": 1},
                "configuration": {"openai": {"api_key_configured": True}},
            }

    monkeypatch.setattr(cli, "runtime", lambda **kwargs: FakeRuntime())
    assert cli.main(["runtime", "--provider", "python-runtime"]) == 0
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


def test_cli_contact_plain_and_json(capsys):
    from agentic_systems import cli

    assert cli.main(["contact", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["author"] == "Jacobo Gerardo González León"
    assert payload["email_1"] == "jacobogerardo.gonzalez@bbva.com"
    assert payload["email_2"] == "jacoboggleon@gmail..com"
    assert payload["linkedin"] == "https://www.linkedin.com/in/jacoboggleon/"
    assert payload["github_repo"] == "https://www.github.com/JacoboGGLeon/agentic_systems"

    assert cli.main(["contact"]) == 0
    out = capsys.readouterr().out
    assert "Jacobo Gerardo González León" in out
    assert "Github Repo" in out


def test_cli_runtime_auto_resolves_vllm_json(capsys, monkeypatch):
    import agentic_systems.core.runtime as runtime_module
    from agentic_systems import cli

    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
    monkeypatch.setattr(runtime_module, "_module_available", lambda name: name == "openai")

    assert cli.main(["runtime", "--provider", "auto", "--provider-priority", "vllm-runtime,openai-runtime,bedrock-runtime", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["selected_provider"] == "vllm-runtime"
    assert payload["model"] == "Qwen/Qwen3-0.6B"
    assert payload["configuration"]["vllm"]["base_url"] == "http://127.0.0.1:8000/v1"
