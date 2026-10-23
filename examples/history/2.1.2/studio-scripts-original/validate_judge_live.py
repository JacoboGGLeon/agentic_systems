"""Calibrate a live judge on explicit fixtures; this is not application E2E evidence."""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import agentic_systems as toolkit
from agentic_systems.contracts import ValidationResult
from agentic_systems_studio import ConversationConfig, load_studio_environment
from agentic_systems_studio.evaluation import build_conversation_judge, evaluate_turn


CASES = (
    (
        "request_echo",
        "Resume la conversación: calculamos 17 por 19 y obtuvimos 323 usando una Tool, la empaquetamos en una Skill y la conectamos a un System.",
        "Resume la conversación: incluye 323, Tool, Skill y System.",
        False,
    ),
    (
        "incorrect_ownership",
        "Explica estos límites según la evidencia: Provider ejecuta inferencia; Framework implementa el agente; System compone unidades; Environment organiza episodios y pasos.",
        "Provider ejecuta las herramientas y System es el propietario de los episodios y pasos temporales.",
        False,
    ),
    (
        "grounded_summary",
        "Resume la conversación: calculamos 17 por 19 y obtuvimos 323 usando una Tool, la empaquetamos en una Skill y la conectamos a un System.",
        "Verificamos el producto 323 mediante una Tool y la empaquetamos en una Skill reutilizable conectada a un System.",
        True,
    ),
)

# Separate examples not used to select the judge instructions above.
HOLDOUT_CASES = (
    (
        "translation_completed",
        "Traduce al español: Good morning.",
        "Buenos días.",
        True,
    ),
    (
        "translation_instruction",
        "Traduce al español: Good morning.",
        "Debes traducir Good morning al español.",
        False,
    ),
    (
        "faithful_paraphrase",
        "Resume esta nota: ayer Ana entregó el informe; mañana Luis lo revisará.",
        "Ana ya entregó el informe y Luis tiene prevista su revisión para mañana.",
        True,
    ),
    (
        "contradicted_summary",
        "Resume esta nota: ayer Ana entregó el informe; mañana Luis lo revisará.",
        "Luis entregó el informe y Ana lo revisó ayer.",
        False,
    ),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--providers", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--suite", choices=("regression", "holdout"), default="regression"
    )
    args = parser.parse_args()
    load_studio_environment()
    rows = []
    for provider in args.providers:
        config = ConversationConfig.from_environment(
            provider=provider, framework="native"
        )
        judge = build_conversation_judge(config)
        if judge is None:
            raise ValueError(
                "Calibration requires an explicitly configured model judge"
            )
        for name, prompt, answer, expected in (
            HOLDOUT_CASES if args.suite == "holdout" else CASES
        ):
            fixture = toolkit.RunResult(
                ok=True,
                text=answer,
                engine="python-runtime",
                model="python-runtime",
                meta={"fixture": True, "framework": "native"},
            )
            case = evaluate_turn(
                fixture,
                prompt,
                judge=judge,
                assertion=lambda result, case: ValidationResult(),
            )
            verdict = case.judge
            valid = bool(
                verdict
                and verdict.execution_ok
                and verdict.certification_recorded
                and verdict.consistent
            )
            ok = valid and verdict.ok == expected
            rows.append(
                {
                    "provider": provider,
                    "name": name,
                    "expected_pass": expected,
                    "ok": ok,
                    "evaluation": case.to_dict(),
                    "judge_execution": judge.last_result.normalized(),
                }
            )
            print(f"[judge calibration] {provider} / {name}: {ok}", flush=True)
    payload = {
        "kind": "live-judge-fixture-calibration",
        "suite": args.suite,
        "candidate_is_fixture": True,
        "package_file": toolkit.__file__,
        "ok": all(row["ok"] for row in rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
