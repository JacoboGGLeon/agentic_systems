from __future__ import annotations

import importlib
import sys
import types

import pytest

from agentic_systems.core import runtime as runtime_core_module
from agentic_systems.core.runtime import (
    RuntimeConfig,
    _auto_reason,
    _auto_unresolved_reason,
    _module_available,
    _provider_available,
    normalize_provider_priority,
    resolve_auto_provider,
)
from agentic_systems.engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_DIRECT_ENGINE,
)
import agentic_systems.factories as factories_module
import agentic_systems.utils as utils_module
from agentic_systems.system import (
    AgenticSystem,
    _merge_skill_inputs,
    _resolve_auto_provider,
)
from agentic_systems.tools import Tool

system_module = importlib.import_module("agentic_systems.system")


def test_system_bedrock_hydration_auto_resolution_and_skill_merge(monkeypatch):
    system = AgenticSystem(model="m", region="r")
    with pytest.raises(TypeError):
        system._register_tool_object(object())

    def broken() -> dict:
        raise RuntimeError("tool broken")

    broken_tool = Tool(broken, name="broken")
    system._register_tool_object(broken_tool)
    broken_result = system._runtime.execute_tool("broken", {})
    assert broken_result.ok is False
    assert "tool broken" in str(broken_result.data)

    runtime_module = types.ModuleType("agentic_systems.providers.bedrock_runtime")

    class FakeBedrockRuntime:
        def __init__(self, **kwargs):
            self.region_name = kwargs["region_name"]
            self.max_tokens_default = kwargs["max_tokens_default"]
            self.temperature_default = kwargs["temperature_default"]
            self._tools = {}
            self.runtime = "runtime"
            self.bedrock = "bedrock"
            self.sts = "sts"

        def run_direct(self):
            return "ok"

    runtime_module.BedrockRuntime = FakeBedrockRuntime
    monkeypatch.setitem(
        sys.modules, "agentic_systems.providers.bedrock_runtime", runtime_module
    )
    system._runtime.runtime = "previous-runtime"
    system._runtime.bedrock = "previous-bedrock"
    system._runtime.sts = "previous-sts"
    hydrated = system._ensure_bedrock_runtime()
    assert hydrated.region_name == "r"
    assert hydrated.runtime == "previous-runtime"
    assert system._ensure_bedrock_runtime() is hydrated

    system2 = AgenticSystem(model="m", region="r")
    system2._engines["bedrock"] = "legacy"
    assert system2._engine("bedrock-runtime") == "legacy"

    monkeypatch.setenv("OPENAI_API_KEY", "key")
    assert (
        _resolve_auto_provider("m", None, (OPENAI_RUNTIME_ENGINE,))
        == OPENAI_RUNTIME_ENGINE
    )
    for key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "VLLM_BASE_URL",
    ):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(runtime_core_module, "_module_available", lambda name: False)
    with pytest.raises(ValueError):
        _resolve_auto_provider(None, None)

    assert normalize_provider_priority(
        "openai-runtime,openai-runtime,bedrock-runtime"
    ) == (OPENAI_RUNTIME_ENGINE, BEDROCK_RUNTIME_ENGINE)
    assert (
        normalize_provider_priority(None, allow_python_fallback=True)[-1]
        == PYTHON_DIRECT_ENGINE
    )
    with pytest.raises(ValueError, match="provider_priority"):
        normalize_provider_priority(["auto"])
    assert resolve_auto_provider(None, [PYTHON_DIRECT_ENGINE]) == PYTHON_DIRECT_ENGINE
    assert (
        RuntimeConfig(provider="auto", allow_python_fallback=True).describe()[
            "selected_provider"
        ]
        == PYTHON_DIRECT_ENGINE
    )
    assert (
        _auto_reason("unexpected-runtime") == "provider selected by configured priority"
    )
    assert "python-runtime fallback" in _auto_unresolved_reason([PYTHON_DIRECT_ENGINE])
    assert _module_available("definitely_missing_agentic_systems_module") is False
    monkeypatch.setattr(
        runtime_core_module.importlib.util,
        "find_spec",
        lambda name: (_ for _ in ()).throw(ValueError("bad spec")),
    )
    assert _module_available("broken") is False

    assert _merge_skill_inputs("one", None) == ["one"]
    assert _merge_skill_inputs(None, ["two"]) == ["two"]
    assert _merge_skill_inputs("one", ["two"]) == ["one", "two"]
    assert _merge_skill_inputs("one", "two") == ["one", "two"]
    assert _provider_available("unknown-runtime", None) is False
    assert factories_module._default_runtime_model("unknown-runtime", None) is None
    assert factories_module._default_runtime_region(BEDROCK_RUNTIME_ENGINE)
    monkeypatch.setattr(
        system_module.importlib.util,
        "find_spec",
        lambda name: (_ for _ in ()).throw(ValueError("bad spec")),
    )
    assert system_module._module_available("broken") is False
    monkeypatch.setattr(
        utils_module.json,
        "loads",
        lambda value: (_ for _ in ()).throw(ValueError("bad json")),
    )
    assert utils_module._looks_like_json_object("{bad}") is False
    monkeypatch.setattr(
        utils_module.re,
        "fullmatch",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad regex")),
    )
    assert utils_module._coerce_field_value("123") == "123"
    assert _merge_skill_inputs("one", ["two"]) == ["one", "two"]
    assert _merge_skill_inputs("one", "two") == ["one", "two"]
    assert _provider_available("unknown-runtime", None) is False
    assert factories_module._default_runtime_model("unknown-runtime", None) is None
    assert factories_module._default_runtime_region(BEDROCK_RUNTIME_ENGINE)
    monkeypatch.setattr(
        system_module.importlib.util,
        "find_spec",
        lambda name: (_ for _ in ()).throw(ValueError("bad spec")),
    )
    assert system_module._module_available("broken") is False
    monkeypatch.setattr(
        utils_module.json,
        "loads",
        lambda value: (_ for _ in ()).throw(ValueError("bad json")),
    )
    assert utils_module._looks_like_json_object("{bad}") is False
    monkeypatch.setattr(
        utils_module.re,
        "fullmatch",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad regex")),
    )
    assert utils_module._coerce_field_value("123") == "123"
