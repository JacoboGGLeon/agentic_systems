
from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

import agentic_systems.agents as agents_mod
import agentic_systems.bedrock_runtime_client as brc
import agentic_systems.contracts as contracts
import agentic_systems.engines.names as names
import agentic_systems.system as system_mod
import agentic_systems.utils as utils
from agentic_systems.final_answer import output_schema
from agentic_systems.results import RunResult


def test_phase7_small_contract_and_engine_residuals(monkeypatch):
    with pytest.raises(ValueError, match="non-empty"):
        names.canonical_engine_name(None)
    assert names.canonical_engine_name("", default="python-direct") == "python-direct"
    assert "bedrock" in names.supported_engine_names(include_aliases=True)
    assert "langgraph" in names.supported_engine_names(include_langgraph=True)

    with pytest.raises(TypeError, match="tool expectation"):
        contracts.normalize_tool_expectation(123)
    assert contracts._clean_tool_names("sumar") == ["sumar"]

    class FakeImportedBedrock:
        pass

    fake_module = ModuleType("agentic_systems.providers.bedrock_runtime")
    fake_module.BedrockRuntime = FakeImportedBedrock
    monkeypatch.setitem(sys.modules, "agentic_systems.providers.bedrock_runtime", fake_module)
    assert brc._import_bedrock_runtime() is FakeImportedBedrock


def test_phase7_agents_output_contract_and_eval_residuals():
    result = RunResult(text="fallback", data={"answer": 42}, ok=True, engine="python-direct")
    agents_mod._coerce_output_data(result, None)
    assert result.final == {"answer": 42}

    projected = RunResult(text="fallback", data={"answer": 42}, ok=True, engine="python-direct")
    agents_mod._coerce_output_data(projected, output_schema(["answer"]))
    assert projected.final == {"answer": 42}

    agent = agents_mod.Agent(name="direct", instructions="x", engine="python-direct")
    with pytest.raises(RuntimeError, match="needs an attached AgenticSystem"):
        agent.eval([])

    with pytest.raises(ValueError, match="policy_tool_budget_too_small"):
        agents_mod.Agent(name="budget", instructions="x", tools=["a", "b"], contract={"must_call": ["a", "b"]}, policy={"max_tool_calls": 1})


def test_phase7_system_auto_provider_and_runtime_copy(monkeypatch):
    monkeypatch.setattr(system_mod, "_openai_signal_present", lambda: True)
    fake_openai = ModuleType("agentic_systems.providers.openai_runtime")
    fake_openai.OpenAIRuntimeProvider = object
    monkeypatch.setitem(sys.modules, "agentic_systems.providers.openai_runtime", fake_openai)
    assert system_mod._resolve_auto_provider(None, None) == "openai-runtime"

    monkeypatch.setattr(system_mod, "_openai_signal_present", lambda: False)
    monkeypatch.setattr(system_mod, "_bedrock_signal_present", lambda region: True)
    fake_bedrock = ModuleType("agentic_systems.providers.bedrock_runtime")

    class FakeBedrockRuntime:
        def __init__(self, *, model_id, region_name, max_tokens_default, temperature_default, disable_openai_runtime_tracing):
            self.model_id = model_id
            self.region_name = region_name or "us-test-1"
            self.max_tokens_default = max_tokens_default
            self.temperature_default = temperature_default
            self.disable_openai_runtime_tracing = disable_openai_runtime_tracing
            self._tools = {}

    fake_bedrock.BedrockRuntime = FakeBedrockRuntime
    monkeypatch.setitem(sys.modules, "agentic_systems.providers.bedrock_runtime", fake_bedrock)
    monkeypatch.setattr(system_mod, "BedrockRuntime", FakeBedrockRuntime, raising=False)
    assert system_mod._resolve_auto_provider(None, "us-test-1") == "bedrock-runtime"

    system = system_mod.AgenticSystem(model="m", region="r")
    previous = SimpleNamespace(
        max_tokens_default=11,
        temperature_default=0.5,
        _tools={"x": object()},
        runtime="runtime-client",
        bedrock="bedrock-client",
        sts="sts-client",
    )
    system._runtime = previous
    hydrated = system._ensure_bedrock_runtime()
    assert hydrated._tools == previous._tools
    assert hydrated.runtime == "runtime-client"
    assert hydrated.bedrock == "bedrock-client"
    assert hydrated.sts == "sts-client"


def test_phase7_utils_residual_branches(capsys):
    output = utils.agent_output(
        RunResult(text="hello world" * 20, data={}, ok=True, engine="openai-runtime"),
        max_string_chars=12,
    )
    assert output["summary"]["answer_preview"]["chars"] > 12

    serialized = {"ok": True, "engine": "python-direct", "tool_events": [], "data": {"x": 1}}
    assert utils._coerce_compare_item(serialized)["run_ok"] is True
    assert utils._coerce_compare_item({"plain": "value"}) == {"plain": "value"}

    assert utils.chain_history_summary(["raw"])[0]["value"] == "raw"
    fields = utils._extract_output_fields(
        object(),
        result_dict={},
        answer_text="",
        data={"fields": {"a": 1}},
        tools=[],
        fields_mapper=None,
    )
    assert fields == {"a": 1}
    with pytest.raises(TypeError, match="fields_mapper"):
        utils._extract_output_fields(object(), result_dict={}, answer_text="", data={}, tools=[], fields_mapper=lambda *_: "bad")

    assert utils._answer_preview("x" * 30, max_string_chars=5)["preview"]
    assert utils._user_facing_answer_text("", {}, {}) == ""
    assert utils._user_facing_answer_text('{"steps": []}', {"steps": []}, {}) == ""
    assert utils._looks_like_json_object("{bad") is False
    assert utils._coerce_field_value("not-a-number") == "not-a-number"

    utils.show({"x": 1}, title="JSON fallback")
    assert "JSON fallback" in capsys.readouterr().out



def test_phase7_final_small_residuals(monkeypatch):
    constructed = RunResult.model_construct(text="txt", data={"x": 1}, final={}, ok=True, engine="python-direct", meta={}, tool_events=[])
    agents_mod._coerce_output_data(constructed, None)
    assert constructed.final == {"x": 1}

    system = system_mod.AgenticSystem(model="m")
    from agentic_systems.tools.tool import Tool
    broken = Tool(name="broken", function=None)
    broken.check = lambda: contracts.ValidationResult(ok=True)
    with pytest.raises(system_mod.ToolContractError, match="no callable"):
        system._register_tool_object(broken)

    monkeypatch.setattr(system_mod, "_openai_signal_present", lambda: True)
    monkeypatch.setattr(system_mod, "_bedrock_signal_present", lambda region: False)
    real_import = __import__

    def block_openai(name, *args, **kwargs):
        if name.endswith("providers.openai_runtime") or name == "agentic_systems.providers.openai_runtime":
            raise ImportError("blocked openai")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", block_openai)
    with pytest.raises(ValueError, match="could not resolve"):
        system_mod._resolve_auto_provider(None, None)

    monkeypatch.setattr(system_mod, "_openai_signal_present", lambda: False)
    monkeypatch.setattr(system_mod, "_bedrock_signal_present", lambda region: True)

    def block_bedrock(name, *args, **kwargs):
        if name.endswith("providers.bedrock_runtime") or name == "agentic_systems.providers.bedrock_runtime":
            raise ImportError("blocked bedrock")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", block_bedrock)
    with pytest.raises(ValueError, match="could not resolve"):
        system_mod._resolve_auto_provider(None, "us-test-1")

    assert utils._looks_like_json_object("{bad}") is False
    monkeypatch.setattr(utils.re, "fullmatch", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("regex")))
    assert utils._coerce_field_value("123") == "123"
