from __future__ import annotations

import builtins

import pytest

from agentic_systems import configure_notebook_environment
from agentic_systems.utils import (
    _clear_dummy_aws_test_credentials,
    _mask_sensitive,
    _mask_string,
    aws_environment_snapshot,
    boto3_session_snapshot,
    repair_ada_credential_chain,
)


def test_configure_notebook_environment_clears_literal_dummy_aws_credentials(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    src = repo / "src"
    repo.mkdir()
    src.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test-session")
    monkeypatch.setenv("AWS_PROFILE", "test-profile")

    configure_notebook_environment(repo)

    assert "AWS_ACCESS_KEY_ID" not in __import__("os").environ
    assert "AWS_SECRET_ACCESS_KEY" not in __import__("os").environ
    assert "AWS_SESSION_TOKEN" not in __import__("os").environ
    assert "AWS_PROFILE" not in __import__("os").environ


def test_clear_dummy_credentials_does_not_remove_real_looking_pair(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAREALLOOKING")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "real-secret")
    assert _clear_dummy_aws_test_credentials() == []
    assert __import__("os").environ["AWS_ACCESS_KEY_ID"] == "AKIAREALLOOKING"

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "not-test")
    assert _clear_dummy_aws_test_credentials() == []
    assert __import__("os").environ["AWS_ACCESS_KEY_ID"] == "test"


def test_aws_environment_snapshot_can_include_values(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    snapshot = aws_environment_snapshot(include_values=True)
    assert snapshot["AWS_REGION"] == "us-east-1"


def test_boto3_session_snapshot_handles_missing_boto3(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "boto3":
            raise ImportError("no boto3")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    snapshot = boto3_session_snapshot("us-east-1")
    assert snapshot["ok"] is False
    assert snapshot["error_type"] == "ImportError"


def test_mask_sensitive_edge_cases():
    assert _mask_sensitive(("secret-value",), parent_key="api_key") == ("secr...alue",)
    assert _mask_sensitive(object(), parent_key="x").__class__ is object
    assert _mask_sensitive("arn:aws:sts::123456789012:assumed-role/demo/session", parent_key="arn") != "arn:aws:sts::123456789012:assumed-role/demo/session"
    assert _mask_string("SET") == "SET"
    assert _mask_string("") == ""
    assert _mask_string("abc", keep_start=6, keep_end=4) == "***"


def test_show_json_prints_explanations(capsys):
    from agentic_systems import show_json

    show_json({"x": 1}, title="T", mask=True, explanations={"x": "meaning"})
    output = capsys.readouterr().out
    assert "Explanation:" in output
    assert "- x: meaning" in output


def test_boto3_session_snapshot_success_path():
    snapshot = boto3_session_snapshot("us-east-1")
    assert set(snapshot) == {"ok", "session_region", "credential_method", "has_credentials"}


def test_repair_ada_credential_chain_reports_and_repairs_env_shadowing(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "abc")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "def")
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    report = repair_ada_credential_chain("us-east-1", force=False)
    assert report["force"] is False
    assert report["repaired"] is False
    assert "before" in report and "after" in report

    forced = repair_ada_credential_chain("us-east-1", force=True)
    assert forced["force"] is True
    assert forced["repaired"] is True
    assert "AWS_ACCESS_KEY_ID" in forced["removed_env_keys"]
    assert "AWS_SECRET_ACCESS_KEY" in forced["removed_env_keys"]


def test_mask_sensitive_arn_without_identifier_key():
    value = "arn:aws:sts::123456789012:assumed-role/demo/session"
    assert _mask_sensitive(value, parent_key="resource") != value
