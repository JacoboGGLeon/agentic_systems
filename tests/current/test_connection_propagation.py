"""Connection options and inherited deadlines reach their execution boundary."""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
import agentic_systems as t
from agentic_systems._context import _active_execution


def test_bedrock_region_reaches_engine():
    config = t.runtime(provider="bedrock-runtime", model="fixture", region="eu-west-1")
    assert config._to_engine().region_name == "eu-west-1"
    assert config.inspect()["region"] == "eu-west-1"


@pytest.mark.parametrize("name", ["openai-agents", "strands"])
def test_framework_forwards_detached_option_mappings(name):
    config = t.framework(name, agent_kwargs={"custom_agent": 7}, run_kwargs={"custom_run": "value"})
    engine = config._to_engine()
    assert dict(engine.agent_kwargs) == {"custom_agent": 7}
    assert dict(engine.run_kwargs) == {"custom_run": "value"}
    assert config.inspect() == {"name": name, "agent_kwargs": {"custom_agent": "int"}, "run_kwargs": {"custom_run": "str"}}


@pytest.mark.parametrize("active,expected", [(None, 10), (SimpleNamespace(remaining_s=None), 10),
    (SimpleNamespace(remaining_s=3), 3), (SimpleNamespace(remaining_s=30), 10),
    (SimpleNamespace(remaining_s=0), 0), (SimpleNamespace(remaining_s=-2), 0)])
def test_actor_session_uses_inherited_remaining_deadline(monkeypatch, active, expected):
    import agentic_systems._contracts as contracts
    import agentic_systems._session as sessions
    observed = []
    session = object()
    output = object()
    @contextmanager
    def scope(value, remaining, *, owner_pid):
        observed.append((value, remaining, owner_pid))
        yield
    monkeypatch.setattr(sessions, "session_scope", scope)
    monkeypatch.setattr(contracts, "_invoke_actor_with_connection", lambda *args: output)
    config = SimpleNamespace(timeout_s=10, session=session, _session_pid=123)
    token = _active_execution.set(active)
    try:
        assert contracts._invoke_actor(object(), config, object(), {}, {}, {}) is output
    finally:
        _active_execution.reset(token)
    assert observed == [(session, expected, 123)]


@pytest.mark.parametrize("field", ["agent_kwargs", "run_kwargs"])
@pytest.mark.parametrize("name", ["native", "openai-agents", "strands"])
def test_owned_options_cannot_be_overridden(name, field):
    with pytest.raises(ValueError):
        t.framework(name, **{field: {"max_tokens": 12}})


@pytest.mark.parametrize("container", ["model_settings", "model_kwargs", "generation_config", "run_config", "config"])
@pytest.mark.parametrize("field", ["agent_kwargs", "run_kwargs"])
def test_nested_owned_options_cannot_be_overridden(container, field):
    with pytest.raises(ValueError, match="Nested SDK options cannot override toolkit-owned configuration"):
        t.framework("openai-agents", **{field: {container: {"nested": [{"max_tokens": 12}]}}})
