import pytest

import agentic_systems as toolkit


@pytest.mark.parametrize("as_mapping", [False, True])
@pytest.mark.parametrize("limit", [17, 233])
def test_prepared_native_handoff_preserves_declared_output_bound(as_mapping, limit):
    policy = {"max_tokens": limit}
    target = toolkit.agent(
        name="arbitrary_destination",
        runtime=toolkit.runtime(provider="python-runtime"),
        framework="openai-agents",
        policy=policy if as_mapping else toolkit.RunPolicy(**policy),
    )
    target.prepare()
    from agents import handoff

    native = target.native_agent
    assert native.model_settings.max_tokens == limit
    assert handoff(native).agent_name == target.name
    assert target.prepare().native_agent.model_settings.max_tokens == limit


def test_prepared_native_settings_preserve_explicit_sdk_bound_without_policy():
    from agents import ModelSettings

    target = toolkit.agent(
        name="configured_destination",
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(
            "openai-agents",
            agent_kwargs={"model_settings": ModelSettings(max_tokens=71)},
        ),
    )
    target.prepare()
    assert target.native_agent.model_settings.max_tokens == 71
