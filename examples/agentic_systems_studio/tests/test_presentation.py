from __future__ import annotations

import agentic_systems as toolkit
import pytest

from agentic_systems_studio.presentation import (
    processing_mark,
    usage_mark,
    validate_generated_agentic_systems_code,
    validate_generated_tool_contracts,
)


def test_processing_mark_uses_observed_runtime_and_tools_only():
    @toolkit.tool
    def safe_calculate(value: int) -> dict:
        return {"result": value}

    agent = toolkit.agent(
        name="processing-mark-probe",
        instructions="Execute the requested deterministic Tool.",
        tools=[safe_calculate],
        runtime=toolkit.runtime(provider="python-runtime"),
    )
    result = agent.run({"tool": "safe_calculate", "input": {"value": 323}})

    mark = processing_mark(result)

    assert mark == (
        "✓ Procesado · provider=python-runtime · framework=native · "
        "tools=safe_calculate"
    )
    assert "reasoning" not in mark.lower()
    assert result.tool_events[0].output["data"]["result"] == 323


def test_processing_mark_reports_no_tool_without_inventing_one():
    result = toolkit.RunResult(
        text="Hola",
        engine="openai-runtime",
        meta={"framework_adapter": "native"},
    )

    assert processing_mark(result).endswith("tools=ninguna")


def test_usage_mark_reports_all_available_fields_without_fabricating_missing_ones():
    result = toolkit.RunResult(
        text="323",
        engine="openai-runtime",
        usage={
            "requests": 2,
            "input_tokens": 400,
            "output_tokens": 25,
            "total_tokens": 425,
            "client_duration_ms": 1234.5,
            "scheduler": {"attempts": 1, "retries": 0, "timed_out": False},
        },
    )

    mark = usage_mark(result)

    for expected in (
        "requests=2",
        "input_tokens=400",
        "output_tokens=25",
        "total_tokens=425",
        "client_duration_ms=1234.5",
        "scheduler.attempts=1",
        "scheduler.retries=0",
        "scheduler.timed_out=False",
    ):
        assert expected in mark
    assert "service_latency_ms" not in mark


def test_usage_mark_is_explicit_when_runtime_reports_nothing():
    result = toolkit.RunResult(text="Hola", engine="python-runtime")

    assert usage_mark(result) == "Usage: no reportado por el runtime"


def test_generated_tool_contract_validation_accepts_public_dictionary_contract():
    validate_generated_tool_contracts(
        """```python
import agentic_systems as toolkit

@toolkit.tool
def multiply(a: int, b: int) -> dict[str, int]:
    return {"result": a * b}
```"""
    )


def test_generated_tool_contract_validation_rejects_non_dictionary_contract():
    with pytest.raises(ValueError, match="dictionary return type"):
        validate_generated_tool_contracts(
            """```python
import agentic_systems as toolkit

@toolkit.tool
def multiply(a: int, b: int) -> int:
    return a * b
```"""
        )


def test_canonical_skill_and_system_factories_are_validated():
    text = """```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

addition = toolkit.skill(name="addition", tools=[add])
system = toolkit.system(runtime=toolkit.runtime(provider="auto"))
```"""
    validate_generated_agentic_systems_code(
        text, required_calls=("skill", "system")
    )


def test_plain_python_without_markdown_fences_is_validated():
    validate_generated_agentic_systems_code(
        """import agentic_systems as toolkit

@toolkit.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}
""",
        required_calls=("tool",),
    )


@pytest.mark.parametrize(
    "text",
    [
        """```python
import agentic_systems as toolkit

@toolkit.skill
class AdditionSkill:
    pass
```""",
        """```python
import agentic_systems as toolkit

class AdditionSkill(toolkit.Skill):
    pass
```""",
    ],
)
def test_noncanonical_skill_shapes_are_rejected(text):
    with pytest.raises(ValueError):
        validate_generated_agentic_systems_code(text, required_calls=("skill",))


def test_unknown_public_factory_kwargs_are_rejected_from_real_signature():
    text = """```python
import agentic_systems as toolkit
skill = toolkit.skill(name="math", tools=[], policies={"strict": True})
```"""

    with pytest.raises(ValueError, match="unsupported keyword.*policies"):
        validate_generated_agentic_systems_code(text, required_calls=("skill",))


@pytest.mark.parametrize(
    "expression",
    (
        "toolkit.skill(name='math', tools=[])(a=1)",
        "math_skill(a=1)",
    ),
)
def test_skill_objects_cannot_be_called_directly(expression):
    prefix = (
        "math_skill = toolkit.skill(name='math', tools=[])\n"
        if expression.startswith("math_skill")
        else ""
    )
    text = (
        "```python\nimport agentic_systems as toolkit\n"
        + prefix
        + f"result = {expression}\n```"
    )

    with pytest.raises(ValueError, match="Skill object"):
        validate_generated_agentic_systems_code(text, required_calls=("skill",))
