from __future__ import annotations

from pathlib import Path

import pytest

from agentic_systems import RunPolicy
from agentic_systems.core.runtime import DOTENV_PATH_ENV_VAR, _load_dotenv
from agentic_systems.integrations.adapters.base import validate_policy_support
from agentic_systems.registry import (
    FRAMEWORK_NAMES,
    PROVIDERS,
    framework_policy_fields,
)


def test_registry_declares_live_flags_authentication_and_policy_support() -> None:
    by_name = {item.name: item for item in PROVIDERS}
    assert by_name["python-runtime"].live_flag is None
    assert by_name["bedrock-runtime"].live_flag == "RUN_BEDROCK_LIVE"
    assert set(by_name["bedrock-runtime"].authentication_modes) == {
        "bedrock-api-key",
        "aws-credential-chain",
    }
    assert all(framework_policy_fields(name) for name in FRAMEWORK_NAMES)
    assert "max_repairs" in framework_policy_fields("native")
    assert "max_repairs" not in framework_policy_fields("strands")


def test_external_frameworks_reject_unsupported_non_default_policy() -> None:
    supported = RunPolicy.for_mode("eval").merge({"max_tool_calls": 2})
    validate_policy_support("strands", supported, "eval")

    unsupported = RunPolicy.for_mode("eval").merge({"max_repairs": 1})
    with pytest.raises(ValueError, match="max_repairs"):
        validate_policy_support("strands", unsupported, "eval")


@pytest.mark.parametrize("framework", ["openai-agents", "strands"])
def test_external_frameworks_accept_declared_noop_policy_values(
    framework: str,
) -> None:
    disabled_repair = RunPolicy.for_mode("eval").merge({"repair": False})

    validate_policy_support(framework, disabled_repair, "eval")


def test_explicit_dotenv_is_authoritative_but_discovery_remains_compatible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / "canonical.env"
    env_file.write_text("CONTRACT_VALUE=dotenv\n", encoding="utf-8")
    monkeypatch.setenv("CONTRACT_VALUE", "process")

    assert _load_dotenv(path=env_file)
    assert __import__("os").environ["CONTRACT_VALUE"] == "dotenv"

    monkeypatch.setenv("CONTRACT_VALUE", "process")
    monkeypatch.setenv(DOTENV_PATH_ENV_VAR, str(env_file))
    assert _load_dotenv()
    assert __import__("os").environ["CONTRACT_VALUE"] == "dotenv"

    discovered = tmp_path / ".env"
    discovered.write_text("CONTRACT_VALUE=nearest\n", encoding="utf-8")
    monkeypatch.delenv(DOTENV_PATH_ENV_VAR)
    monkeypatch.setenv("CONTRACT_VALUE", "process")
    assert _load_dotenv(tmp_path)
    assert __import__("os").environ["CONTRACT_VALUE"] == "process"


def test_explicit_missing_dotenv_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Canonical dotenv file does not exist"):
        _load_dotenv(path=tmp_path / "missing.env")
