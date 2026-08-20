from __future__ import annotations

import json
import time

import agentic_systems as toolkit

PROMPT = "Responde en una sola linea y exactamente con el texto: AGENTIC_SYSTEMS_LIVE_OK"


@toolkit.tool(name="noop", description="Return the supplied value unchanged.")
def noop(value: str = "") -> dict:
    return {"value": value}


for provider in ("bedrock-runtime", "openai-runtime", "ollama-runtime"):
    started = time.perf_counter()
    try:
        runtime = toolkit.runtime(provider=provider)
        agent = toolkit.agent(
            name=f"live-{provider}",
            instructions=(
                "Sigue literalmente la instruccion del usuario. "
                "No llames herramientas salvo que sea imprescindible."
            ),
            tools=[noop],
            runtime=runtime,
            framework="native",
        )
        result = agent.run(PROMPT)
        payload = {
            "provider": provider,
            "framework": "native",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "ok": result.ok,
            "text": result.text,
            "engine": result.engine,
            "model": result.model,
            "usage": result.usage,
            "errors": result.errors,
            "tool_events": len(result.tool_events),
        }
    except Exception as exc:
        payload = {
            "provider": provider,
            "framework": "native",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "ok": False,
            "text": "",
            "errors": [{"code": type(exc).__name__, "message": str(exc)}],
        }
    print(json.dumps(payload, ensure_ascii=False, default=str), flush=True)
