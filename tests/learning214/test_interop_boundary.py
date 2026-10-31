import pytest
from agentic_systems_studio.lab.interop import observed_output

EXPECTED = {"value": 43, "trail": ["native"]}


@pytest.mark.parametrize(
    "value",
    [
        EXPECTED,
        {"data": EXPECTED},
        {
            "kind": "object",
            "tool_name": "mark_native",
            "ok": True,
            "data": EXPECTED,
            "meta": {"serializer": "BedrockRuntime.ToolEnvelope.v1"},
        },
    ],
)
def test_known_envelopes_preserve_exact_business_data(value):
    assert observed_output(value, "mark_native", EXPECTED) == EXPECTED


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "object", "tool_name": "wrong", "ok": True, "data": EXPECTED},
        {"kind": "object", "tool_name": "mark_native", "ok": False, "data": EXPECTED},
        {
            "kind": "object",
            "tool_name": "mark_native",
            "ok": True,
            "data": {"value": 999, "trail": ["native"]},
        },
        {"data": EXPECTED, "unrecognized": True},
    ],
)
def test_wrong_identity_failure_and_changed_data_stay_rejected(value):
    with pytest.raises(ValueError):
        observed_output(value, "mark_native", EXPECTED)


def test_studio_system_composition_preserves_one_business_envelope():
    from types import SimpleNamespace
    from agentic_systems_studio._graph import pipeline
    from agentic_systems_studio.systems import compose_systems

    units = [
        SimpleNamespace(
            system=pipeline("increment", (lambda data: {"value": data["value"] + 1},))
        )
        for _ in range(2)
    ]
    sequential = compose_systems(units).run({"payload": {"value": 1}})
    assert sequential.ok and sequential.data == {"payload": {"value": 3}}
    parallel = compose_systems(units, mode="parallel").run({"payload": {"value": 1}})
    assert parallel.ok and parallel.data["results"] == {
        "system_0": {"value": 2},
        "system_1": {"value": 2},
    }
