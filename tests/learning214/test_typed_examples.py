"""Portable Tool calls must preserve the deterministic business oracle."""

import importlib
from pathlib import Path
import pytest
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[2]
CASES = sorted(
    p
    for group in ("applications", "patterns")
    for p in (ROOT / "examples" / group).glob("*/example.py")
    if "class Payload(Closed)" in p.read_text(encoding="utf-8")
)


@pytest.mark.parametrize("framework", ("native", "openai-agents", "strands"))
@pytest.mark.parametrize("path", CASES, ids=lambda p: p.parent.name)
def test_typed_arguments_preserve_business_output(path, framework):
    module = importlib.import_module(
        ".".join(path.relative_to(ROOT).with_suffix("").parts)
    )
    oracle = module.run()  # Includes the original business assertions.
    actor = toolkit.Agent(
        "typed-contract",
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(framework),
        skills=(module.capability,),
    )
    result = actor.run(module.sample)
    assert result.ok and result.data == oracle.data
    assert result.check_invariants().ok
    assert result.usage.get("inference_requests", 0) == 0


def test_missing_amount_is_not_an_explicit_null():
    from pydantic import ValidationError
    from examples.applications.data_quality.example import Payload

    assert Payload(rows=[{"id": 1, "amount": None}]).model_dump() == {
        "rows": [{"id": 1, "amount": None}]
    }
    with pytest.raises(ValidationError):
        Payload(rows=[{"id": 1}])
