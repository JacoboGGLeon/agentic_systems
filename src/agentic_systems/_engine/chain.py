"""Primitive Bedrock chains without agents, tools, environments or evals."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .bedrock_runtime_client import BedrockRuntimeClient
from .results import RunResult

ChainStepKind = Literal["complete", "markdown_answer"]


@dataclass(frozen=True)
class ChainStep:
    """Serializable chain step for primitive completion workflows."""

    name: str
    kind: ChainStepKind
    input: dict[str, Any]
    output: dict[str, Any] = field(default_factory=dict)


class Chain:
    """Small sequential wrapper around ``BedrockRuntimeClient``.

    A chain is deliberately weaker than an agent: it does not decide which tool
    to call, does not manage an environment, and does not perform evals. It is a
    clean place for plain completions, translation, summarization and markdown
    Q&A before introducing agentic behavior.
    """

    def __init__(self, runtime: BedrockRuntimeClient, *, instructions: str = "") -> None:
        self.runtime = runtime
        self.instructions = instructions
        self.steps: list[ChainStep] = []

    def complete(
        self,
        prompt: str,
        *,
        name: str = "complete",
        instructions: str | None = None,
        **kwargs: Any,
    ) -> RunResult:
        result = self.runtime.complete(
            prompt,
            instructions=instructions if instructions is not None else self.instructions,
            data={"kind": "chain_completion", "step": name},
            **kwargs,
        )
        self.steps.append(
            ChainStep(
                name=name,
                kind="complete",
                input={"prompt": prompt, "instructions": instructions if instructions is not None else self.instructions},
                output={"ok": result.ok, "text": result.text, "usage": result.usage},
            )
        )
        return result

    def translate(
        self,
        text: str,
        *,
        target_language: str,
        name: str = "translate",
        **kwargs: Any,
    ) -> RunResult:
        prompt = f"Traduce el siguiente texto a {target_language}. Devuelve sólo la traducción.\n\n{text}"
        return self.complete(prompt, name=name, **kwargs)

    def answer_from_markdown(
        self,
        *,
        path: str | Path,
        question: str,
        name: str = "markdown_answer",
        instructions: str | None = None,
        **kwargs: Any,
    ) -> RunResult:
        result = self.runtime.answer_from_markdown(
            path=path,
            question=question,
            instructions=instructions if instructions is not None else self.instructions,
            **kwargs,
        )
        self.steps.append(
            ChainStep(
                name=name,
                kind="markdown_answer",
                input={"path": str(path), "question": question, "instructions": instructions if instructions is not None else self.instructions},
                output={"ok": result.ok, "text": result.text, "usage": result.usage},
            )
        )
        return result

    def history(self) -> list[dict[str, Any]]:
        """Return JSON-like step history."""

        return [
            {"name": step.name, "kind": step.kind, "input": step.input, "output": step.output}
            for step in self.steps
        ]


__all__ = ["Chain", "ChainStep", "ChainStepKind"]
