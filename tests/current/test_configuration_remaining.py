"""Configuration preserves model identity and rejects owned option overrides."""
from types import SimpleNamespace
import pytest
import agentic_systems as t
from agentic_systems._configuration import _check_framework_options


def test_artifact_preserves_all_optional_fields():
    values = {"model": "adapter-model", "base_model": "base-model", "adapter_path": "adapter/path",
        "tokenizer": "tokenizer-id", "revision": "revision-id", "quantization": "awq", "metadata": {"owner": "fixture"}}
    artifact = t.model_artifact(**values)
    assert artifact.inspect() == values
    engine = artifact._to_engine()
    assert (engine.model_id, engine.base_model_id, engine.adapter_path, engine.tokenizer_id,
            engine.revision, engine.quantization, engine.metadata) == (
        "adapter-model", "base-model", "adapter/path", "tokenizer-id", "revision-id", "awq", {"owner": "fixture"})
    config = t.model_server(artifact).inspect()["configuration"]["artifact"]
    for key, value in values.items():
        assert config[key] == value
    assert not {"model_id", "base_model_id", "tokenizer_id"} & config.keys()


@pytest.mark.parametrize("model", [None, "", "  ", 12])
def test_model_identity_error_is_actionable(model):
    with pytest.raises(ValueError) as caught:
        t.model_artifact(model)
    assert str(caught.value) == "Model identity is required"


@pytest.mark.parametrize("field", ["agent", "run"])
def test_native_framework_rejects_even_unowned_options(field):
    with pytest.raises(ValueError) as caught:
        _check_framework_options("native", {"custom": 1} if field == "agent" else {},
                                 {"custom": 1} if field == "run" else {})
    assert str(caught.value) == "This adapter does not forward native SDK options"


@pytest.mark.parametrize("key", ["runtime", "model", "provider", "api_key", "endpoint", "timeout_s", "max_retries",
    "max_tokens", "max_turns", "max_tool_calls", "max_concurrency", "backoff_s", "contract", "policy", "limits"])
@pytest.mark.parametrize("field", ["agent", "run"])
def test_each_owned_option_rejected_directly_and_in_sdk_objects(key, field):
    args = [{key: 1}, {}] if field == "agent" else [{}, {key: 1}]
    with pytest.raises(ValueError) as caught:
        _check_framework_options("openai-agents", *args)
    assert str(caught.value) == "Framework options cannot override toolkit-owned configuration"
    settings = {"config": SimpleNamespace(nested=(SimpleNamespace(), {key: 1}))}
    args = [settings, {}] if field == "agent" else [{}, settings]
    with pytest.raises(ValueError) as caught:
        _check_framework_options("openai-agents", *args)
    assert str(caught.value) == "Nested SDK options cannot override toolkit-owned configuration"


def test_none_nested_options_are_not_overrides():
    _check_framework_options("openai-agents", {"model_settings": SimpleNamespace(max_tokens=None)}, {})


def test_runtime_defaults_remain_stable():
    config = t.runtime(provider="python-runtime")
    assert (config.timeout_s, config.max_retries, config.max_tool_calls, config.max_turns,
            config.max_tokens, config.backoff_s, config.max_concurrency) == (60, 0, 5, 6, None, 0, 1)


@pytest.mark.parametrize("args", [[], (1,)])
def test_server_extra_arguments_reject_invalid_container_or_members(args):
    with pytest.raises(ValueError) as caught:
        t.model_server(t.model_artifact("fixture"), extra_args=args)
    assert str(caught.value) == "extra_args cannot override managed server parameters"


def test_server_accepts_unmanaged_arguments_and_rejects_unknown_profile():
    server = t.model_server(t.model_artifact("fixture"), extra_args=("--custom=one=two",))
    assert "--custom=one=two" in server.command
    with pytest.raises(ValueError) as caught:
        t.model_server(t.model_artifact("fixture"), profile="unknown")
    assert str(caught.value) == "Unknown exact server profile"


def test_iam_authentication_inspection_never_resolves_credentials():
    import boto3
    session = boto3.Session(region_name="eu-west-1")
    assert t.runtime(provider="bedrock-runtime", model="fixture", session=session).inspect()["authentication_mode"] == "aws-session-iam"


def test_opaque_framework_settings_are_accepted():
    _check_framework_options("openai-agents", {"config": 7}, {})


@pytest.mark.parametrize("profile", ["medium", "power", "custom"])
def test_server_forwards_every_nondefault_setting(monkeypatch, profile):
    import agentic_systems._engine.serving.vllm as impl
    observed = {}
    original = impl.vllm_server_spec
    def capture(artifact, **kwargs):
        observed.update(kwargs)
        return original(artifact, **kwargs)
    monkeypatch.setattr(impl, "vllm_server_spec", capture)
    options = dict(profile=profile, served_model_name="served", host="0.0.0.0", port=9123,
        tool_call_parser="custom-parser", reasoning_parser="custom-reasoner", enable_auto_tool_choice=False,
        api_key="fixture-key", startup_timeout_s=42.0, log_path="custom.log", binary="custom-vllm",
        extra_args=("--custom=1",), gpu_memory_utilization=0.6, max_model_len=2048, max_num_seqs=4)
    t.model_server(t.model_artifact("fixture"), **options)
    assert observed == options


def test_managed_argument_rejected_with_multiple_equals():
    with pytest.raises(ValueError):
        t.model_server(t.model_artifact("fixture"), extra_args=("--host=one=two",))


def test_server_health_retains_endpoint(monkeypatch):
    server = t.model_server(t.model_artifact("fixture"))
    resource = server._resource
    endpoint = resource.endpoint
    monkeypatch.setattr(type(resource), "health", lambda self: SimpleNamespace(status="ready", endpoint=endpoint, detail="healthy"))
    assert server.health().endpoint == server.endpoint
    assert server.health().status == "ready"
