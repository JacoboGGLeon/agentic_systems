import asyncio
from dataclasses import replace
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, StrictInt

import agentic_systems as a
from test_grammar import assert_result


class Input(BaseModel):
    value: StrictInt


class Output(BaseModel):
    value: StrictInt


@pytest.mark.parametrize("provider", ["python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"])
def test_all_explicit_providers_and_readonly_configuration(provider):
    options = {} if provider == "python-runtime" else {"model": "explicit-model", "api_key": "fixture-secret", "endpoint": "https://fixture.invalid"}
    if provider == "bedrock-runtime":
        options["region"] = "us-east-1"
    config = a.runtime(provider=provider, timeout_s=4, max_retries=2, max_tool_calls=3, max_turns=8, backoff_s=0.1, max_concurrency=2, **options)
    description = config.inspect()
    assert description["provider"] == provider and description["max_turns"] == 8
    assert "fixture-secret" not in json.dumps(description) and "fixture-secret" not in repr(config)
    assert not hasattr(config, "coerce") and not hasattr(config, "model_id")
    with pytest.raises(AttributeError):
        config.provider = "auto"


@pytest.mark.parametrize("options", [{"provider": "auto"}, {"provider": "python"}, {"provider": "python-runtime", "max_turns": 0},
    {"provider": "python-runtime", "max_tool_calls": True}, {"provider": "python-runtime", "api_key": "x"},
    {"provider": "openai-runtime", "region": "irrelevant"}, {"provider": "openai-runtime", "max_tokens": 0},
    {"provider": "openai-runtime", "backoff_s": -1}, {"provider": "openai-runtime", "timeout_s": float('inf')}])
def test_invalid_runtime_fields_rejected(options):
    with pytest.raises((TypeError, ValueError)):
        a.runtime(**options)


@pytest.mark.parametrize("name", ["native", "openai-agents", "strands"])
def test_four_real_framework_paths_with_python_runtime(name):
    @a.tool
    def echo(value: int) -> dict:
        return {"value": value}
    actor = a.Agent("operator", runtime=a.runtime(provider="python-runtime"), framework=a.framework(name),
                    skills=(a.skill(name="echo", tools=[echo], instructions="Use the supplied Tool"),))
    result = actor.run({"tool": "echo", "input": {"value": 9}})
    assert result.ok and result.data["value"] == 9, result.to_dict()
    assert result.usage.get("inference_requests", 0) == 0
    assert_result(result)


@pytest.mark.parametrize("kind", ["agent_kwargs", "run_kwargs"])
def test_framework_forwarding_and_reserved_names(kind):
    config = a.framework("openai-agents", **{kind: {"custom_option": "fixture-secret"}})
    assert config.inspect()[kind] == {"custom_option": "str"}
    with pytest.raises(TypeError):
        config.agent_kwargs["mutated"] = True
    with pytest.raises(ValueError):
        a.framework("openai-agents", **{kind: {"max_tokens": 999}})
    with pytest.raises(TypeError):
        a.framework("openai-agents", **{kind: []})


def test_tool_schema_validation_async_and_no_aliases():
    @a.tool(name="validated", description="Explicit schemas", input_schema=Input, output_schema=Output, metadata={"domain": "test"})
    def validated(data: Input) -> Output:
        return Output(value=data.value + 1)
    assert validated.run({"value": 3}).data == {"value": 4}
    assert asyncio.run(validated.arun({"value": 3})).data == {"value": 4}
    invalid = validated.run({"value": "not-int"})
    assert not invalid.ok and not invalid.tool_events[0].ok
    assert_result(invalid)
    assert validated.inspect()["input_schema"]["type"] == "object"
    for removed in ("info", "describe", "check", "function"):
        assert not hasattr(validated, removed)
    with pytest.raises(TypeError):
        validated.run(input_payload={"value": 3})
    with pytest.raises(TypeError):
        a.tool(strict=False)
    with pytest.raises(TypeError):
        a.tool(input_schema={})(lambda x: {})
    with pytest.raises(ValueError):
        a.tool(lambda x: {})


def test_portable_skill_relative_imports_survive_loading(tmp_path):
    (tmp_path / "SKILL.md").write_text("# Portable", encoding="utf-8")
    (tmp_path / "helper.py").write_text("def compute(value): return {'value':value+1}\n", encoding="utf-8")
    (tmp_path / "skill.py").write_text("import agentic_systems as a\n@a.tool\ndef inc(value:int)->dict:\n    from .helper import compute\n    return compute(value)\ndef build_skill():\n    return a.skill(name='portable',tools=[inc],instructions='Increment',version='1.0',metadata={'portable':True})\n", encoding="utf-8")
    loaded = a.load_skill(tmp_path)
    assert loaded.inspect()["instructions"] == "Increment"
    assert loaded.tools[0].run({"value": 5}).data == {"value": 6}
    retained_tool = a.load_skill(tmp_path).tools[0]
    import gc
    gc.collect()
    assert retained_tool.run({"value": 5}).data == {"value": 6}
    assert a.Agent("loaded", a.Action("inc", "inc"), skills=(loaded,)).run({"value": 5}).ok
    for removed in ("compose", "tool", "prompt", "info", "check", "available_tools"):
        assert not hasattr(loaded, removed)
    with pytest.raises(TypeError):
        a.load_skill(loaded)
    with pytest.raises(TypeError):
        a.load_skill(tmp_path, ignored=True)
    (tmp_path / "skill.py").write_text("def build(): return None\n", encoding="utf-8")
    with pytest.raises(ValueError):
        a.load_skill(tmp_path)


def test_skill_identity_conflicts_and_removed_metadata_contracts():
    @a.tool
    def echo(value: int) -> dict:
        return {"value": value}
    one = a.skill(name="one", tools=[echo])
    assert a.skill(name="described", description="Display only")._to_engine().instructions == ""
    assert a.skill(name="instructed", instructions="Exact instructions")._to_engine().instructions == "Exact instructions"
    assert a.Agent("same", a.Action("echo", "echo"), skills=(one, a.skill(name="two", tools=[echo]))).run({"value": 1}).ok
    another = a.tool(echo._function, name="echo")
    with pytest.raises(ValueError):
        a.Agent("conflict", a.Action("echo", "echo"), skills=(one, a.skill(name="two", tools=[another]))).compile()
    with pytest.raises(ValueError):
        a.skill(name="duplicate", tools=[echo, echo])
    with pytest.raises(TypeError):
        a.skill(name="bad", policy={})


@pytest.mark.parametrize("provider", ["openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"])
@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_model_boundary_forwarding_and_structured_output_without_inference(monkeypatch, provider, framework):
    import agentic_systems._engine.factories as implementation
    from agentic_systems._engine.results import RunResult as EngineResult
    seen = []
    class FixtureActor:
        def run(self, value):
            return EngineResult(text='{"value":7}', data={}, engine=provider, model="fixture-model", usage={"requests": 1}, meta={"fixture": True})
    def factory(**kwargs):
        seen.append(kwargs)
        return FixtureActor()
    monkeypatch.setattr(implementation, "agent", factory)
    schema = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"], "additionalProperties": False}
    actor = a.Agent("model", runtime=a.runtime(provider=provider, model="fixture-model", max_tokens=20, max_turns=10),
        framework=a.framework(framework, agent_kwargs={"fixture_option": "yes"} if framework in {"openai-agents", "strands"} else None), contract={"output_schema": schema}, policy={"temperature": 0.0})
    actor.inspect()
    assert not seen
    result = actor.run({"value": 0})
    assert result.ok and result.data == {"value": 7}, result.to_dict()
    assert seen[0]["policy"]["max_tokens"] == 20 and seen[0]["policy"]["max_turns"] == 10
    assert seen[0]["framework"].name == framework
    assert seen[0]["framework"].agent_kwargs == ({"fixture_option": "yes"} if framework in {"openai-agents", "strands"} else {})
    assert_result(result)
    # Requests recorded in this result are synthetic fixture data, never real inference.


@pytest.mark.parametrize("contract", [{"must_call": []}, {"require_no_unresolved_tool_failures": True}, {"failure_policy": False},
    {"completion": "required_tools_ok"}, {"tool_expectation": {"exactly": []}},
    {"output_schema": {"$ref": "https://fixture.invalid/schema"}}])
def test_contract_aliases_and_remote_schema_rejected_without_provider(contract):
    with pytest.raises((TypeError, ValueError)):
        a.Agent("model", runtime=a.runtime(provider="openai-runtime", model="fixture-model"), contract=contract).compile()


def test_structured_output_failure_preserves_original_result(monkeypatch):
    import agentic_systems._grammar as grammar
    monkeypatch.setattr(grammar, "_invoke_actor", lambda *args: a.RunResult(data={"value": "invalid"}, engine="openai-runtime", model="fixture-model"))
    schema = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]}
    result = a.Agent("model", runtime=a.runtime(provider="openai-runtime", model="fixture-model"), contract={"output_schema": schema}).run({})
    assert not result.ok and result.data == {"value": "invalid"}
    assert any(e["code"] == "output_schema_mismatch" for n in result.walk() for e in n.errors)
    assert_result(result)


def test_result_fields_lineage_serialization_and_secret_redaction():
    result = a.RunResult(data={"value": 3}, text="Answer", final={"summary": "Three"}, messages=({"role": "user", "content": "input"},),
        usage={"inference_requests": 0, "tool_calls": 0}, raw_responses=({"api_key": "fixture-secret"},),
        validation={"ok": True, "issues": []}, meta={"name": "record", "input": {"value": 3}})
    assert_result(result)
    assert "fixture-secret" not in json.dumps(result.to_dict())
    assert result.trace("full") == result.to_dict()
    assert result.trace()["data"] == {"value": 3}
    memory = result.lineage(name="example", question="What?", goal="Explain", tags=["fixture"], metadata={"version": "test"}, max_tool_rows=1)
    assert memory.to_dict()["question"] == "What?" and memory.explain()["ok"]
    assert len(memory.to_prompt_context(max_chars=100)) <= 100
    with pytest.raises(ValueError):
        result.trace("unknown")
    invalid = replace(result, ok=True, errors=({"code": "unexpected"},))
    assert not invalid.check_invariants().ok


def test_serving_all_fields_are_explicit_and_inspection_is_pure(tmp_path):
    artifact = a.model_artifact("fixture/model", base_model="fixture/base", adapter_path="adapter", tokenizer="fixture/tokenizer",
                                revision="revision-id", quantization="int8", metadata={"fixture": True})
    assert artifact.inspect()["revision"] == "revision-id"
    server = a.model_server(artifact, profile="custom", served_model_name="fixture", host="127.0.0.1", port=8123,
        tool_call_parser="hermes", reasoning_parser="fixture-parser", enable_auto_tool_choice=True, api_key="fixture-secret",
        startup_timeout_s=1.0, log_path=str(tmp_path / "log"), binary="fixture-vllm", extra_args=("--dtype", "auto"),
        gpu_memory_utilization=0.5, max_model_len=1024, max_num_seqs=2)
    description = server.inspect()
    assert server.endpoint.url.endswith(':8123/v1') and server.endpoint.model == "fixture"
    assert "fixture-secret" not in json.dumps(description) and "fixture-secret" not in repr(server.command)
    assert "--api-key" in server._resource.command and "fixture-secret" in server._resource.command
    for method in ("runtime", "running", "model_dump", "coerce"):
        assert not hasattr(server, method)
    with pytest.raises(ValueError):
        a.model_server(artifact, extra_args=("--port=9999",))
    with pytest.raises(TypeError):
        a.model_server("fixture/model")
    with pytest.raises(TypeError):
        a.model_server(artifact, spec={})


def test_server_lifecycle_with_fake_process_and_http(monkeypatch, tmp_path):
    import agentic_systems._engine.serving.vllm as implementation
    state = {"started": False, "terminated": False}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"data":[{"id":"fixture"}]}'
    class Opener:
        def open(self, *args, **kwargs):
            if not state["started"]:
                raise OSError("not started")
            return Response()
    class Process:
        pid = 123
        def poll(self): return 0 if state["terminated"] else None
        def terminate(self): state["terminated"] = True
        def wait(self, timeout): return 0
    def popen(*args, **kwargs):
        state["started"] = True
        return Process()
    monkeypatch.setattr(implementation.shutil, "which", lambda name: str(tmp_path / "fake-vllm"))
    monkeypatch.setattr(implementation.urllib.request, "build_opener", lambda *args: Opener())
    server = a.model_server(a.model_artifact("fixture"), log_path=str(tmp_path / "log"), startup_timeout_s=1.0)
    server._resource._popen_factory = popen
    endpoint = server.start()
    assert endpoint.owned and endpoint.pid == 123 and server.health().status == "healthy"
    server.stop()
    assert state["terminated"] and not server.endpoint.owned


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_canonical_order_example(backend):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples"))
    from order_fulfillment import verify
    report = verify(backend)
    assert report["cases_passed"] == 7 and report["evaluation"]["data"]["passed"] == 6
