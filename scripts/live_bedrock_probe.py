from __future__ import annotations

import json
import time

import agentic_systems as toolkit


@toolkit.tool(name="noop", description="Return the supplied value unchanged.")
def noop(value: str = "") -> dict:
    return {"value": value}


started = time.perf_counter()
runtime = toolkit.runtime(provider="bedrock-runtime")
agent = toolkit.agent(
    name="live-bedrock-runtime",
    instructions=(
        "Sigue literalmente la instruccion del usuario. "
        "No llames herramientas salvo que sea imprescindible."
    ),
    tools=[noop],
    runtime=runtime,
    framework="native",
)
result = agent.run(
    "Responde en una sola linea y exactamente con el texto: "
    "AGENTIC_SYSTEMS_LIVE_OK"
)
print(
    json.dumps(
        {
            "provider": "bedrock-runtime",
            "framework": "native",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "ok": result.ok,
            "text": result.text,
            "engine": result.engine,
            "model": result.model,
            "usage": result.usage,
            "errors": result.errors,
            "tool_events": len(result.tool_events),
        },
        ensure_ascii=False,
        default=str,
    )
)
