from __future__ import annotations

import json
from pathlib import Path

import agentic_systems as lab
from agentic_systems.cli import main


def test_cli_version_prints_package_version(capsys) -> None:
    assert main(["version"]) == 0

    out = capsys.readouterr().out.strip()
    assert out == "1.0.0"


def test_cli_doctor_json_reports_engines(capsys) -> None:
    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "agentic-systems"
    assert "python-runtime" in payload["supported_engines"]
    assert "environment" in payload
    assert "optional_dependencies" in payload


def test_cli_doctor_loads_local_dotenv_without_printing_secret(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret-from-dotenv\n", encoding="utf-8")

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
    assert payload["count"] == len(lab.PUBLIC_API)
    assert payload["symbols"] == list(lab.PUBLIC_API)


def test_cli_api_can_filter_symbols(capsys) -> None:
    assert main(["api", "--tier", "public", "--contains", "runtime", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] >= 1
    assert all("runtime" in name.lower() for name in payload["symbols"])


def test_tutorials_legacy_human_output_wrapper_removed() -> None:
    assert not Path("tutorials/human_output.py").exists()
