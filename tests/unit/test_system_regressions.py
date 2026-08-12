import dataclasses
import os
from typing import Any, Dict

import pytest
from pydantic import BaseModel

from agentic_systems import (
    AgenticSystem,
    RunResult,
)
from agentic_systems.contracts import ValidationResult
from agentic_systems.providers.openai_runtime import OpenAIRuntimeProvider
from agentic_systems.system import InspectReport, _return_annotation_is_dict


def build_system(strict=True, defaults=None):
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(
        model="demo-model", region="us-east-1", strict=strict, defaults=defaults
    )


class EchoEngine:
    name = "bedrock"

    def run(self, agent, input, policy, *, mode="default"):
        if isinstance(input, BaseModel):
            payload = input.model_dump(mode="json")
        else:
            payload = input if isinstance(input, dict) else {"input": input}
        text = payload.get("text") or payload.get("input") or "ok"
        data = payload.get("data") or {"answer": str(text), "score": 1}
        return RunResult(
            text=str(text),
            data=data,
            ok=True,
            engine=self.name,
            model=agent.model,
            mode=mode,
        )

    async def arun(self, agent, input, policy, *, mode="default"):
        return self.run(agent, input, policy, mode=mode)


class InputModel(BaseModel):
    input: str


class OutputModel(BaseModel):
    answer: str
    score: int = 1


def test_system_public_helpers_and_registration_errors(monkeypatch):
    system = build_system(
        strict=False, defaults={"max_tokens": None, "temperature": None}
    )

    @system.tool(name="loose")
    def loose() -> list:
        """Loose mode tool."""
        return [1]

    assert system.execute_tool("loose", {}).data == {"items": [1]}
    assert system.skills == ()
    assert system.toolkit("same") is system.toolkit("same")
    assert system.export_tool_specs(["loose"])[0]["name"] == "loose"

    with pytest.raises(ValueError, match="LangGraph"):
        system.agent(name="g", instructions="x", engine="langgraph")
    with pytest.raises(KeyError, match="Unknown tools"):
        system.agent(name="missing", instructions="x", tools=["missing"])
    with pytest.raises(ValueError, match="Unknown runtime/provider"):
        system._engine("unknown")
    assert isinstance(system._engine("openai-runtime"), OpenAIRuntimeProvider)

    assert InspectReport(ok=True).raise_if_errors()["ok"] is True

    bad = InspectReport(ok=False, errors=[{"x": 1}])
    with pytest.raises(ValueError, match="inspect failed"):
        bad.raise_if_errors()

    def no_return(a: int):
        return {"a": a}

    def old_style() -> Dict[str, Any]:
        return {"ok": True}

    def broken_annotation() -> "MissingType":  # noqa: F821 - intentionally unresolved
        return {"ok": True}

    assert _return_annotation_is_dict(no_return) is False
    assert _return_annotation_is_dict(old_style) is True
    assert _return_annotation_is_dict(broken_annotation) is False

    # inspect warnings from runtime registry and errors from strict return validation
    strict_system = build_system(strict=True)

    @strict_system.tool
    def valid_tool() -> dict:
        """Valid tool."""
        return {"ok": True}

    def no_return_for_spec():
        return {"ok": True}

    spec = strict_system._runtime._tools["valid_tool"]
    strict_system._runtime._tools["valid_tool"] = dataclasses.replace(
        spec, func=no_return_for_spec
    )
    report = strict_system.inspect()
    assert report["ok"] is False
    assert report["errors"][0]["issue"] == "tool_return_annotation_must_be_dict"

    warning_system = build_system(strict=False)

    @warning_system.tool(name="warn_tool", description=" ")
    def warn_tool() -> dict:
        return {"ok": True}

    warning_report = warning_system.inspect()
    assert warning_report["warnings"][0]["source"] == "runtime_registry"

    class WarningAgent:
        name = "warning_agent"

        def validate(self):
            result = ValidationResult(ok=True)
            result.add("agent_warning", "only warning", severity="warning")
            return result

    warning_system._agents.append(WarningAgent())
    assert any(
        issue.get("code") == "agent_warning"
        for issue in warning_system.inspect()["warnings"]
    )
