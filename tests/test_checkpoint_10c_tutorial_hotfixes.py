from __future__ import annotations

import inspect

from agentic_systems.bedrock_runtime_client import BedrockRuntimeClient


def test_chain_markdown_prompt_prevents_source_reprint() -> None:
    source = inspect.getsource(BedrockRuntimeClient.answer_from_markdown)
    required = [
        "No copies ni reimprimas el Markdown completo",
        "Devuelve sólo la respuesta final",
        "no reproduzcas el documento fuente",
    ]
    missing = [needle for needle in required if needle not in source]
    assert missing == []
