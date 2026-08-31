"""Validate the conversational Studio against explicitly configured providers."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from agentic_systems_studio import (
    ConversationConfig,
    build_conversational_system,
    load_studio_environment,
)
from agentic_systems_studio.presentation import (
    processing_mark,
    usage_mark,
    validate_generated_agentic_systems_code,
    validate_generated_tool_contracts,
)


DEFAULT_PROVIDERS = (
    "python-runtime",
    "openai-runtime",
    "ollama-runtime",
    "bedrock-runtime",
)
PROMPT = (
    "Usa la calculadora para verificar 17 por 19. Después usa la Skill de "
    "Agentic Systems para proponer cómo convertir ese cálculo en una Skill y un "
    "System reutilizables. Responde en español."
)
FOLLOW_UP = (
    "Resume nuestra propuesta en una sola frase que conserve 323, Skill y System."
)
LONG_PROMPTS = (
    "Nuestro proyecto se llama Boreal. Confirma que recibiste el contexto sin "
    "repetir el nombre.",
    "El número base es 17. Confirma que lo conservarás sin repetirlo ni hacer "
    "ningún cálculo.",
    "Usa la calculadora para multiplicar el número base por 19 y conserva el "
    "resultado como evidencia.",
    "Con ese cálculo, consulta la Skill de Agentic Systems y diseña una Tool "
    "reutilizable que reciba base y multiplicador con su contrato público correcto.",
    "Ahora explica cómo empaquetar esa Tool dentro de una Skill reutilizable e "
    "incluye el código exacto con la fábrica pública correspondiente.",
    "Ahora compón esa Skill dentro de un System y explica qué frontera aporta.",
    "Distingue Provider de Framework en una sola frase, sin cambiar la propuesta.",
    "Resume la conversación: incluye 323, Tool, Skill y System. Si el nombre del "
    "proyecto ya no está en el contexto acotado, dilo sin inventarlo.",
)
QUOTA_FIELDS = (
    "requests",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "client_duration_ms",
    "service_latency_ms",
)


def _tool_names(result: Any) -> list[str]:
    return [str(event.name) for event in result.tool_events]


def _contains_private_reasoning(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ("<thinking", "</thinking>", "<reasoning", "</reasoning>")
    )


def _contains_any(text: str, alternatives: tuple[str, ...]) -> bool:
    return any(value in text for value in alternatives)


def _assert_reusable_binary_tool(text: str) -> None:
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL)
    if not blocks and text.strip().startswith(
        ("import agentic_systems", "from agentic_systems")
    ):
        blocks = [text.strip()]
    for block in blocks:
        tree = ast.parse(block)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = {ast.unparse(item) for item in node.decorator_list}
            if "toolkit.tool" in decorators and len(node.args.args) >= 2:
                return
    raise AssertionError("Reusable multiplier Tool must accept base and multiplier.")


def _assert_common_result(result: Any, *, provider: str) -> list[str]:
    if not result.ok:
        raise AssertionError(result.errors)
    result.check_invariants().raise_if_failed()
    if result.engine != provider:
        raise AssertionError({"expected_provider": provider, "actual": result.engine})
    if any(node.meta.get("fallback_provider") for node in result.walk()):
        raise AssertionError("Provider fallback was observed.")
    if _contains_private_reasoning(result.text):
        raise AssertionError("Private reasoning leaked into public text.")
    validate_generated_tool_contracts(result.text)

    tools = _tool_names(result)
    if "prepare_conversation_context" not in tools:
        raise AssertionError({"missing_tool": "prepare_conversation_context", "tools": tools})
    return tools


def _assert_live_result(result: Any, *, provider: str, follow_up: bool) -> None:
    tools = _assert_common_result(result, provider=provider)

    if provider == "python-runtime":
        if "hello_world" not in tools or "no tengo mente" not in result.text.lower():
            raise AssertionError({"invalid_python_control": result.text, "tools": tools})
        return

    required = (
        set() if follow_up else {"safe_calculate", "inspect_agentic_systems_grammar"}
    )
    if missing := required.difference(tools):
        raise AssertionError({"missing_tools": sorted(missing), "tools": tools})
    lowered = result.text.lower()
    if not {"323", "skill", "system"}.issubset(
        {token for token in ("323", "skill", "system") if token in lowered}
    ):
        raise AssertionError({"semantic_answer_failed": result.text})
    if follow_up and result.data.get("context_summary", {}).get("history_turns", 0) < 2:
        raise AssertionError({"conversation_memory_failed": result.data})
    usage = result.normalized().get("usage") or {}
    if not usage.get("requests") or not usage.get("total_tokens"):
        raise AssertionError({"missing_live_usage": usage})


def _assert_long_turn(result: Any, *, provider: str, index: int) -> None:
    tools = _assert_common_result(result, provider=provider)
    lowered = result.text.lower()
    if provider == "python-runtime":
        if "hello_world" not in tools or "no tengo mente" not in lowered:
            raise AssertionError({"invalid_python_control": result.text, "tools": tools})
        return

    usage = result.normalized().get("usage") or {}
    if not usage.get("requests") or not usage.get("total_tokens"):
        raise AssertionError({"missing_live_usage": usage})
    if "boreal" in lowered:
        raise AssertionError({"context_instruction_failed": result.text})
    if index == 1 and "17" in lowered:
        raise AssertionError({"number_instruction_failed": result.text})
    if index in (0, 1) and tools != ["prepare_conversation_context"]:
        raise AssertionError({"acknowledgement_tool_overreach": tools})
    if index == 2 and ("safe_calculate" not in tools or "323" not in lowered):
        raise AssertionError({"calculation_turn_failed": result.text, "tools": tools})
    if index == 3 and (
        "inspect_agentic_systems_grammar" not in tools or "tool" not in lowered
    ):
        raise AssertionError({"grammar_turn_failed": result.text, "tools": tools})
    if index == 3:
        _assert_reusable_binary_tool(result.text)
    required_factories = {
        3: ("tool",),
        4: ("skill",),
        5: ("skill", "system"),
    }.get(index, ())
    validate_generated_agentic_systems_code(
        result.text,
        required_calls=required_factories,
    )
    expected = {
        4: ("skill", "habilidad"),
        5: ("system", "sistema"),
    }.get(index)
    if expected and not _contains_any(lowered, expected):
        raise AssertionError({"composition_turn_failed": result.text})
    if index == 4 and "toolkit.skill" not in lowered:
        raise AssertionError({"canonical_skill_factory_missing": result.text})
    if index == 5 and not (
        "toolkit.system" in lowered
        or (
            _contains_any(lowered, ("compos",))
            and _contains_any(lowered, ("boundary", "frontera"))
        )
    ):
        raise AssertionError({"system_boundary_failed": result.text})
    if index == 6 and not (
        _contains_any(lowered, ("provider", "proveedor"))
        and _contains_any(lowered, ("framework", "marco"))
    ):
        raise AssertionError({"portability_turn_failed": result.text})
    if index == 6 and not (
        _contains_any(lowered, ("inference", "inferencia", "runtime"))
        and _contains_any(lowered, ("orchestr", "orquest"))
    ):
        raise AssertionError({"provider_framework_contract_failed": result.text})
    if index == len(LONG_PROMPTS) - 1:
        required = {"323", "tool", "skill", "system"}
        if not all(token in lowered for token in required):
            raise AssertionError({"long_summary_failed": result.text})
        if not _contains_any(
            lowered,
            (
                "no está",
                "no esta",
                "no disponible",
                "no se ha",
                "no se menciona",
                "ya no",
                "not present",
            ),
        ):
            raise AssertionError({"project_availability_invented": result.text})
        if _contains_any(lowered, ("proyecto 323", "project 323")):
            raise AssertionError({"project_identity_invented": result.text})
        history_turns = result.data.get("context_summary", {}).get("history_turns")
        if history_turns != 12:
            raise AssertionError({"bounded_context_size": history_turns})


def _run_provider(provider: str) -> dict[str, Any]:
    config = ConversationConfig.from_environment(provider=provider, framework="native")
    studio = build_conversational_system(config)
    first = studio.run(PROMPT)
    _assert_live_result(first, provider=provider, follow_up=False)
    history = [
        {"role": "user", "content": PROMPT},
        {"role": "assistant", "content": first.text},
    ]
    second = studio.run(FOLLOW_UP, history=history)
    _assert_live_result(second, provider=provider, follow_up=True)
    return {
        "provider": provider,
        "framework": "native",
        "model": second.model,
        "ok": True,
        "turns": [
            {
                "prompt": PROMPT,
                "answer": first.text,
                "tools": _tool_names(first),
                "processing": processing_mark(first),
                "usage": first.normalized().get("usage") or {},
                "usage_mark": usage_mark(first),
                "lineage": first.lineage().to_dict(),
            },
            {
                "prompt": FOLLOW_UP,
                "answer": second.text,
                "tools": _tool_names(second),
                "processing": processing_mark(second),
                "usage": second.normalized().get("usage") or {},
                "usage_mark": usage_mark(second),
                "lineage": second.lineage().to_dict(),
            },
        ],
    }


def _accumulate_usage(
    cumulative: dict[str, int | float | bool], result: Any
) -> dict[str, int | float | bool]:
    usage = result.normalized().get("usage") or {}
    for field in QUOTA_FIELDS:
        value = usage.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            cumulative[field] = cumulative.get(field, 0) + value
    scheduler = usage.get("scheduler") or {}
    for field in ("attempts", "retries"):
        value = scheduler.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            key = f"scheduler.{field}"
            cumulative[key] = cumulative.get(key, 0) + value
    cumulative["scheduler.timed_out"] = bool(
        cumulative.get("scheduler.timed_out", False)
        or scheduler.get("timed_out", False)
    )
    return dict(cumulative)


def _turn_payload(
    prompt: str,
    result: Any,
    *,
    cumulative_usage: dict[str, int | float | bool] | None = None,
) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "answer": result.text,
        "tools": _tool_names(result),
        "processing": processing_mark(result),
        "usage": result.normalized().get("usage") or {},
        "usage_mark": usage_mark(result),
        "lineage": result.lineage().to_dict(),
        "cumulative_usage": cumulative_usage or {},
        "context_history_turns": result.data.get("context_summary", {}).get(
            "history_turns", 0
        ),
        "context_memory": result.data.get("context_summary", {}).get("memory", {}),
        "response_validation": result.data.get("response_validation", {}),
    }


def _run_long_provider(provider: str) -> dict[str, Any]:
    config = ConversationConfig.from_environment(provider=provider, framework="native")
    studio = build_conversational_system(config)
    history: list[dict[str, str]] = [
        {
            "role": "assistant",
            "content": "Ready. Ask a question or request a verified calculation.",
        }
    ]
    turns: list[dict[str, Any]] = []
    cumulative_usage: dict[str, int | float | bool] = {}
    validation_errors: list[dict[str, Any]] = []
    model = config.model
    for index, prompt in enumerate(LONG_PROMPTS):
        result = studio.run(prompt, history=history)
        validation_error: str | None = None
        try:
            _assert_long_turn(result, provider=provider, index=index)
        except (AssertionError, SyntaxError, ValueError) as exc:
            validation_error = str(exc)
            validation_errors.append(
                {"turn": index + 1, "prompt": prompt, "error": validation_error}
            )
        quota = _accumulate_usage(cumulative_usage, result)
        payload = _turn_payload(prompt, result, cumulative_usage=quota)
        payload["semantic_validation"] = {
            "ok": validation_error is None,
            "error": validation_error,
        }
        turns.append(payload)
        history.extend(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": result.text},
            ]
        )
        model = result.model
    return {
        "provider": provider,
        "framework": "native",
        "model": model,
        "ok": not validation_errors,
        "validation_errors": validation_errors,
        "turns": turns,
        "usage_totals": dict(cumulative_usage),
        "context_memory": {
            **turns[-1]["context_memory"],
            "final_observed_messages": turns[-1]["context_history_turns"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", action="append", dest="provider_items")
    parser.add_argument("--providers", nargs="+")
    parser.add_argument("--long", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    environment_path = load_studio_environment()
    selected = [*(args.providers or ()), *(args.provider_items or ())]
    providers = selected or list(DEFAULT_PROVIDERS)
    runner = _run_long_provider if args.long else _run_provider
    rows = [runner(provider) for provider in providers]
    report = {
        "schema_version": "agentic-systems.studio-live-validation/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": str(environment_path),
        "prompt": PROMPT,
        "follow_up": FOLLOW_UP,
        "scenario": "long-bounded-conversation" if args.long else "two-turn",
        "long_prompts": list(LONG_PROMPTS) if args.long else [],
        "providers": rows,
        "ok": all(row["ok"] for row in rows),
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.quiet:
        print(
            json.dumps(
                {
                    "output": str(args.output) if args.output else None,
                    "scenario": report["scenario"],
                    "providers": [
                        {
                            "provider": row["provider"],
                            "ok": row["ok"],
                            "turns": len(row["turns"]),
                            "usage_totals": row.get("usage_totals", {}),
                            "validation_errors": row.get("validation_errors", []),
                        }
                        for row in rows
                    ],
                    "ok": report["ok"],
                },
                indent=2,
                ensure_ascii=True,
            )
        )
    else:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
