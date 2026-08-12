from __future__ import annotations

import importlib

import pytest

import agentic_systems.agents as agents_mod
import agentic_systems.contracts as contracts
import agentic_systems.core.runtime as runtime_core_mod
import agentic_systems.utils as utils
from agentic_systems.results import RunResult
system_mod = importlib.import_module("agentic_systems.system")


def test_runtime_module_availability_and_environment_paths(monkeypatch):
    constructed = RunResult.model_construct(text="txt", data={"x": 1}, final={}, ok=True, engine="python-runtime", meta={}, tool_events=[])
    agents_mod._coerce_output_data(constructed, None)
    assert constructed.final == {"x": 1}

    system = system_mod.AgenticSystem(model="m")
    from agentic_systems.tools.tool import Tool
    broken = Tool(name="broken", function=None)
    broken.check = lambda: contracts.ValidationResult(ok=True)
    with pytest.raises(system_mod.ToolContractError, match="no callable"):
        system._register_tool_object(broken)

    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE", "VLLM_BASE_URL"):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(runtime_core_mod, "_module_available", lambda name: False)
    with pytest.raises(ValueError, match="could not resolve"):
        system_mod._resolve_auto_provider(None, None)


    assert utils._looks_like_json_object("{bad}") is False
    monkeypatch.setattr(utils.re, "fullmatch", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("regex")))
    assert utils._coerce_field_value("123") == "123"
