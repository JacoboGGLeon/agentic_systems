"""ADA diagnostics stay optional, read-only and free of credential material."""

import json
import os

import agentic_systems_ada as ada


def test_ada_diagnostics_never_resolve_credentials_or_repair_environment(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "private-fixture-value")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "private-fixture-secret")
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    class Session:
        region_name = "us-east-2"

        def get_credentials(self):
            raise AssertionError("Unexpected credential resolution")

        def client(self, *args, **kwargs):
            raise AssertionError("Unexpected service access")

    before = dict(os.environ)
    result = ada.diagnose(session=Session())
    assert result["static_pair_without_session_token"]
    assert not result["services_checked"] and not result["ada_validated"]
    assert not result["credentials_resolved"] and dict(os.environ) == before
    assert "private-fixture" not in json.dumps(result)


def test_addon_cli_is_explicit_about_its_scope(capsys):
    assert ada.main(["doctor"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["scope"] == "configuration-only"
    assert result["environment_mutated"] is False
