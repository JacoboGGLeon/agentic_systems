from __future__ import annotations

import json

import agentic_systems as lab
from agentic_systems.cli import main


def test_cli_runtime_json_and_rich_output(capsys, monkeypatch):
    import agentic_systems.cli as cli

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
    import agentic_systems.cli as cli

    assert cli.main(["doctor", "--json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["package"] == "agentic-systems"
    assert "supported_engines" in doctor
    assert "vllm-runtime" in doctor["supported_engines"]
    assert "has_vllm_base_url" in doctor["environment"]
    assert {row["name"] for row in doctor["providers"]} == {
        "python-runtime",
        "openai-runtime",
        "ollama-runtime",
        "vllm-runtime",
        "bedrock-runtime",
    }
    assert {row["name"] for row in doctor["frameworks"]} == {
        "native",
        "langgraph",
        "openai-agents",
        "strands",
    }
    assert (
        next(row for row in doctor["providers"] if row["name"] == "python-runtime")[
            "ready"
        ]
        is True
    )

    assert cli.main(["api", "--tier", "public", "--contains", "runtime", "--json"]) == 0
    api = json.loads(capsys.readouterr().out)
    assert api["tier"] == "public"
    assert any("runtime" in identifier.lower() for identifier in api["ids"])


def test_cli_public_api_plain_json_and_runtime_safe_configuration(capsys, monkeypatch):
    import agentic_systems.cli as cli

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
    import agentic_systems.cli as cli

    assert cli.main(["contact", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["author"] == "Jacobo Gerardo González León"
    assert payload["email_1"] == "jacobogerardo.gonzalez@bbva.com"
    assert payload["email_2"] == "jacoboggleon@gmail.com"
    assert payload["linkedin"] == "https://www.linkedin.com/in/jacoboggleon/"
    assert (
        payload["github_repo"] == "https://www.github.com/JacoboGGLeon/agentic_systems"
    )

    assert cli.main(["contact"]) == 0
    out = capsys.readouterr().out
    assert "Jacobo Gerardo González León" in out
    assert "Github Repo" in out


def test_cli_runtime_auto_resolves_vllm_json(capsys, monkeypatch):
    import agentic_systems.core.runtime as runtime_module
    import agentic_systems.cli as cli

    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
    monkeypatch.setattr(
        runtime_module, "_module_available", lambda name: name == "openai"
    )

    assert (
        cli.main(
            [
                "runtime",
                "--provider",
                "auto",
                "--provider-priority",
                "vllm-runtime,openai-runtime,bedrock-runtime",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["selected_provider"] == "vllm-runtime"
    assert payload["model"] == "Qwen/Qwen3-0.6B"
    assert payload["configuration"]["vllm"]["base_url"] == "http://127.0.0.1:8000/v1"


def test_cli_version_prints_package_version(capsys) -> None:
    assert main(["version"]) == 0

    out = capsys.readouterr().out.strip()
    assert out == lab.__version__


def test_cli_doctor_json_reports_engines(capsys) -> None:
    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "agentic-systems"
    assert "python-runtime" in payload["supported_engines"]
    assert "environment" in payload
    assert "optional_dependencies" in payload


def test_cli_doctor_loads_local_dotenv_without_printing_secret(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=secret-from-dotenv\n", encoding="utf-8"
    )

    assert main(["doctor", "--json"]) == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["dotenv_loaded"] is True
    assert payload["environment"]["has_openai_api_key"] is True
    assert "secret-from-dotenv" not in out


def test_cli_runtime_describes_auto_provider(capsys) -> None:
    assert main(["runtime", "--provider", "auto", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_provider"] in {"auto", "openai-runtime", "bedrock-runtime"}
    assert payload["mode"] in {"auto", "auto-unresolved"}
    assert "scheduler" in payload


def test_cli_public_api_lists_recommended_symbols(capsys) -> None:
    assert main(["public-api"]) == 0

    out = capsys.readouterr().out
    assert "agent\n" in out
    assert "runtime\n" in out
    assert "human_result\n" in out


def test_cli_api_public_tier_exposes_complete_public_api(capsys) -> None:
    assert main(["api", "--tier", "public", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["tier"] == "public"
    assert payload["count"] == lab.api_contract()["entry_count"]
    assert payload["ids"] == lab.api_contract()["ids"]


def test_cli_api_can_filter_contract_ids(capsys) -> None:
    assert main(["api", "--tier", "public", "--contains", "runtime", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] >= 1
    assert all("runtime" in identifier.lower() for identifier in payload["ids"])


def test_cli_model_server_inspect_is_read_only_and_secret_safe(capsys):
    assert (
        main(
            [
                "model-server",
                "inspect",
                "--model",
                "unsloth/Qwen3-0.6B",
                "--profile",
                "fast",
                "--reasoning-parser",
                "qwen3",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "vllm"
    assert payload["spec"]["profile"] == "fast"
    assert payload["endpoint"]["owned"] is False
    assert payload["endpoint"]["pid"] is None
    assert "--reasoning-parser" in payload["command"]
    assert "api_key" not in payload["spec"]
    assert payload["endpoint"]["api_key_configured"] is True


def test_cli_model_server_inspect_renders_rich_panel(capsys) -> None:
    assert main(["model-server", "inspect", "--model", "served"]) == 0

    output = capsys.readouterr().out
    assert "Model Server" in output
    assert '"backend": "vllm"' in output
