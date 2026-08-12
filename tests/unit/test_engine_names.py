from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest

import agentic_systems.bedrock_runtime_client as brc
import agentic_systems.contracts as contracts
import agentic_systems.engines.names as names

system_mod = importlib.import_module("agentic_systems.system")


def test_contract_serialization_and_engine_name_paths(monkeypatch):
    with pytest.raises(ValueError, match="non-empty"):
        names.canonical_engine_name(None)
    assert names.canonical_engine_name("", default="python-runtime") == "python-runtime"
    assert "bedrock" not in names.supported_engine_names()
    assert "langgraph" in names.supported_engine_names(include_langgraph=True)

    with pytest.raises(TypeError, match="tool expectation"):
        contracts.normalize_tool_expectation(123)
    assert contracts._clean_tool_names("sumar") == ["sumar"]

    class FakeImportedBedrock:
        pass

    fake_module = ModuleType("agentic_systems.providers.bedrock_runtime")
    fake_module.BedrockRuntime = FakeImportedBedrock
    monkeypatch.setitem(
        sys.modules, "agentic_systems.providers.bedrock_runtime", fake_module
    )
    assert brc._import_bedrock_runtime() is FakeImportedBedrock
