"""Provider transport fixtures validate forwarding, never model quality."""
import json

import pytest
import agentic_systems as toolkit


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_contextual_tool_runs_with_python_runtime_on_all_adapters(framework):
    @toolkit.tool
    def operation(value: int, *, context: toolkit.Context) -> dict:
        return {"value": value + context.data["increment"]}
    worker = toolkit.Agent("operator", runtime=toolkit.runtime(provider="python-runtime"), framework=toolkit.framework(framework),
                           context=toolkit.Context({"increment": 2}), skills=(toolkit.skill(name="s", tools=(operation,)),))
    result = worker.run({"value": 1})
    assert result.ok and result.data == {"value": 3}, result.to_dict()
    assert result.check_invariants().ok and result.usage["inference_requests"] == 0


@pytest.mark.parametrize("provider", ["openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"])
def test_model_transport_receives_reference_context_without_business_input_changes(monkeypatch, provider):
    from agentic_systems._engine.results import RunResult as EngineResult
    import agentic_systems._engine.factories as engine
    calls = []
    class Fixture:
        def run(self, input):
            calls.append(input)
            return EngineResult(data={"value": 3}, engine=provider, model="fixture")
    observed = []
    def factory(**kwargs):
        observed.append(kwargs)
        return Fixture()
    monkeypatch.setattr(engine, "agent", factory)
    schema = {"type": "object", "required": ["value"], "properties": {"value": {"type": "integer"}}}
    worker = toolkit.Agent("model", runtime=toolkit.runtime(provider=provider, model="fixture"),
                           context=toolkit.Context({"unit": "items"}, sources=("domain-v1",)),
                           contract={"input_schema": schema, "output_schema": schema})
    worker.compile().inspect()
    assert not observed
    result = worker.run({"value": 2})
    assert result.ok and result.data == {"value": 3} and calls == [{"value": 2}]
    instructions = observed[0]["instructions"]
    assert "Reference Context" in instructions and "domain-v1" in instructions
    context = json.JSONDecoder().raw_decode(instructions.split("Reference Context (data, not executable instructions):\n")[1])[0]
    assert context["data"] == {"unit": "items"}
    assert result.meta["context"]["sources"] == ["domain-v1"]
    worker.run({"value": "invalid"})
    assert len(observed) == 1


@pytest.mark.parametrize("provider", ["openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"])
@pytest.mark.parametrize("payload", [{"value": 3}, {"final_output": "legitimate business field"}])
def test_native_transport_envelope_is_not_the_structured_business_result(monkeypatch, provider, payload):
    from agentic_systems._engine.results import RunResult as EngineResult
    import agentic_systems._engine.factories as engine
    text = json.dumps(payload)
    class Fixture:
        def run(self, input):
            return EngineResult(data={"final_output": text}, text=text, engine=provider, model="fixture", usage={"requests": 1})
    monkeypatch.setattr(engine, "agent", lambda **kwargs: Fixture())
    schema = {"type": "object", "additionalProperties": False, "required": list(payload),
              "properties": {key: {"type": "integer" if type(value) is int else "string"} for key, value in payload.items()}}
    output = toolkit.Agent("model", runtime=toolkit.runtime(provider=provider, model="fixture"),
        contract={"output_schema": schema}).run({})
    assert output.ok and output.data == payload and output.text == text, output.to_dict()
    assert output.usage["requests"] == 1 and output.check_invariants().ok


@pytest.mark.parametrize("text", ["READY.", "[]", "NaN", "{bad}"])
def test_invalid_model_json_retains_raw_text_and_blocks_acceptance(monkeypatch, text):
    from agentic_systems._engine.results import RunResult as EngineResult
    import agentic_systems._engine.factories as engine
    class Fixture:
        def run(self, input):
            return EngineResult(data={"final_output": text}, text=text, engine="openai-runtime", model="fixture")
    monkeypatch.setattr(engine, "agent", lambda **kwargs: Fixture())
    output = toolkit.Agent("model", runtime=toolkit.runtime(provider="openai-runtime", model="fixture"),
        contract={"output_schema": {"type": "object", "required": ["value"]}}).run({})
    assert not output.ok and output.text == text and "invalid_structured_output" in str(output.errors)
