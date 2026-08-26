from __future__ import annotations

import importlib

import agentic_systems.core.runtime as runtime_module
import pytest

from agentic_systems.core.runtime import RuntimeConfig, _find_dotenv, _load_dotenv
from agentic_systems.engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
)

system_module = importlib.import_module("agentic_systems.system")


def test_runtime_config_coerce_dotenv_and_describe(monkeypatch, tmp_path):
    base = RuntimeConfig(
        provider="openai-runtime",
        model_id="m",
        region_name="r",
        scheduler={"timeout_s": 7},
    )
    assert RuntimeConfig.coerce(base) is base
    coerced = RuntimeConfig.coerce(
        base, model="m2", region="r2", provider="python-runtime"
    )
    assert coerced.provider == PYTHON_RUNTIME_ENGINE
    assert coerced.model_id == "m2"
    assert coerced.region_name == "r2"
    assert coerced.scheduler.timeout_s == 7
    assert RuntimeConfig.coerce(None).provider == BEDROCK_RUNTIME_ENGINE
    assert (
        RuntimeConfig.coerce({"provider": "openai-runtime"}).provider
        == OPENAI_RUNTIME_ENGINE
    )
    with pytest.raises(TypeError):
        RuntimeConfig.coerce("bad")

    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# ignored\nOPENAI_API_KEY='from-dotenv'\nBADLINE\nAWS_REGION=us-test-1\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(nested)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    assert _find_dotenv(nested) == env_file
    assert _load_dotenv(nested) is True
    outside = tmp_path.parent / "outside_without_env"
    outside.mkdir(exist_ok=True)
    assert _load_dotenv(outside) is False
    assert (
        RuntimeConfig(
            provider="auto",
            metadata={
                "resolution": {
                    "selected_provider": OPENAI_RUNTIME_ENGINE,
                    "mode": "test",
                },
                "openai": {"configured": True},
            },
        ).describe()["selected_provider"]
        == OPENAI_RUNTIME_ENGINE
    )
    explicit = RuntimeConfig(
        provider="auto",
        metadata={
            "resolution": {"selected_provider": "python-runtime", "mode": "test"},
            "bedrock": {"configured": True},
        },
    ).describe()
    assert explicit["selected_provider"] == PYTHON_RUNTIME_ENGINE
    assert explicit["configuration"]["bedrock"]["configured"] is True
    assert (
        runtime_module._auto_reason("ollama-runtime")
        == "OLLAMA_MODEL/OLLAMA_BASE_URL config detected"
    )
