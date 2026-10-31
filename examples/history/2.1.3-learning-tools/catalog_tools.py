"""Render/check reference cards offline. Never import the SDK or call a provider."""

from __future__ import annotations
import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "examples"
STATUSES = {
    "accepted-2.1.2",
    "historical-pass",
    "mixed",
    "offline-only",
    "designed",
    "pending-2.1.2",
    "retired",
    "configuration-only",
    "live-tested",
}
WHEEL = "2c14a8e6f871fcc455acbf899db851130c49a129ba988821d6656e90ebc3d47b"
SUMMARY_URL = "https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.2/final-certification-summary.json"
STATUS_LABELS = {
    "offline-only": "Offline ejecutado",
    "configuration-only": "Configuración; entorno pendiente",
    "live-tested": "Live: escenario probado",
    "designed": "Diseñado; sin ejecución",
    "accepted-2.1.2": "Aceptado en 2.1.2",
    "historical-pass": "Evidencia histórica",
    "mixed": "Resultados mixtos",
    "pending-2.1.2": "Pendiente en 2.1.2",
    "retired": "Retirado",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def link(ref: dict, parent: Path) -> str:
    target = ref["target"]
    if not target.startswith("https://"):
        # All cards live two directories below examples/.
        prefix = "../" * len(parent.relative_to(ROOT).parts)
        target = prefix + target
    return f"[{ref['label']}]({target})"


def render(catalog: dict) -> dict[Path, str]:
    files = {}
    lines = [
        "# Examples",
        "",
        "Ejemplos de la API única **2.1.3**. Elige una tarea, importa `run` y observa el resultado.",
        "",
        "```python",
        "from examples.applications.research_synthesis.example import run",
        "",
        "result = run()",
        "result.data",
        "```",
        "",
        "El resultado también conserva evidencia de su ejecución:",
        "",
        "```python",
        "result.ok",
        'result.lineage(name="research").to_dict()',
        "```",
        "",
        "Empieza por [los seis flujos](grammar_tour/README.md), continúa con [pedidos](order_fulfillment/README.md) y abre [Studio](agentic_systems_studio/README.md).",
        "[Tutorials](../tutorials/README.md) enseña los conceptos; aquí se muestran implementaciones.",
        "",
        "Con el SDK instalado, importa estos ejemplos desde la raíz del repositorio. Son material del repositorio, separado del paquete de PyPI.",
        "",
        "Los resultados offline, live y de configuración se indican por separado. Un candidato guardado no es una generación de un modelo.",
        "",
    ]
    groups = {
        "applications": "Aplicaciones",
        "patterns": "Patrones",
        "validation": "Integraciones y contratos",
    }
    for group, title in groups.items():
        lines += [
            "## " + title,
            "",
            "| Ejemplo | Para qué sirve | Validación actual |",
            "|---|---|---|",
        ]
        for entry in catalog["entries"]:
            if entry["group"] != group:
                continue
            slug = group + "/" + entry["id"]
            status = STATUS_LABELS[entry["validation"]["status"]]
            lines.append(
                f"| [{entry['title']}]({slug}/README.md) | {entry['purpose']} | {status} |"
            )
            parent = HOME / slug
            card = ["# " + entry["title"], "", entry["purpose"], ""]
            entrypoint = entry.get("entrypoint")
            if entrypoint:
                module, function = entrypoint.split(":")
                card += [
                    "```python",
                    "from " + module + " import " + function,
                    "",
                    "result = " + function + "()",
                    "result",
                    "```",
                    "",
                ]
            card += [entry["flow"], "", "Código:"]
            card += ["- " + link(ref, parent) for ref in entry["sources"]]
            card += [
                "",
                "Validación: **" + status + "**. " + entry["validation"]["scope"],
                "",
            ]
            card += [
                "- " + link(ref, parent) for ref in entry["validation"]["evidence"]
            ]
            if "historical_validation" in entry:
                old = entry["historical_validation"]
                card += [
                    "",
                    "<details>",
                    "<summary>Evidencia del experimento anterior</summary>",
                    "",
                    "Estado anterior: " + old["status"] + ". " + old["scope"],
                    "",
                    "La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.",
                    "",
                ]
                card += ["- " + link(ref, parent) for ref in old["evidence"]]
                card += ["", "</details>"]
            files[parent / "README.md"] = "\n".join(card) + "\n"
        lines.append("")
    lines += [
        "[Resultados y límites de la nueva validación](../docs/LEARNING_VALIDATION_213.md).",
        "[RunResult y Lineage Memory de cada ejemplo y notebook](../docs/RUNRESULTS_LINEAGE_213.md): resultados observados y evidencia de cómo se obtuvieron.",
        "[Inventario exhaustivo de notebooks y gramática](../docs/NOTEBOOK_INVENTORY_213.md).",
        "[Catálogo completo y evidencia anterior](catalog.json).",
        "",
        "vLLM/Colab, AWS IAM y ADA IAM conservan la ejecución en su entorno como pendiente.",
        "",
        "Mantenimiento del catálogo y validadores: [guía de desarrollo](../docs/VALIDATION_213.md).",
        "",
    ]
    files[HOME / "README.md"] = "\n".join(lines)
    return files


def validate(catalog: dict) -> None:
    require(catalog["baseline"]["version"] == "2.1.2", "Wrong baseline version")
    require(catalog["baseline"]["wheel_sha256"] == WHEEL, "Wrong baseline wheel")
    ids = set()
    for entry in catalog["entries"]:
        require(bool(re.fullmatch(r"[a-z][a-z0-9_]*", entry["id"])), "Invalid ID")
        require(entry["id"] not in ids, "Duplicate ID")
        ids.add(entry["id"])
        require(
            entry["group"] in {"applications", "patterns", "validation"},
            "Invalid group",
        )
        validation = entry["validation"]
        require(validation["status"] in STATUSES, "Invalid validation status")
        require(
            bool(validation["scope"] and validation["evidence"]),
            "Missing evidence scope",
        )
        if validation["status"] == "accepted-2.1.2":
            require(validation["wheel_sha256"] == WHEEL, "Wrong accepted wheel")
            require(
                any(ref["target"] == SUMMARY_URL for ref in validation["evidence"]),
                "Missing published acceptance summary",
            )
        for ref in entry["sources"] + validation["evidence"]:
            if not ref["target"].startswith("https://"):
                target = (ROOT / ref["target"]).resolve()
                target.relative_to(ROOT)
                require(".tmp" not in target.parts, "Nonportable local evidence link")
                require(target.is_file(), f"Missing reference: {ref['target']}")
    tree = ast.parse(
        (ROOT / "src/agentic_systems/__init__.py").read_text(encoding="utf-8")
    )
    stable = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
    )
    require(len(stable) == 18, "Wrong current API symbol count")
    require(
        not {"agent", "system", "graph", "Route"}.intersection(stable),
        "Alternative constructors in API",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog = json.loads((HOME / "catalog.json").read_text(encoding="utf-8"))
    validate(catalog)
    files = render(catalog)
    for path, content in files.items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        else:
            require(
                path.is_file() and path.read_text(encoding="utf-8") == content,
                f"Stale card: {path.relative_to(ROOT)}",
            )
    print(
        f"OK: {len(catalog['entries'])} catalog entries, {len(files)} pages, one 18-symbol API; no inference."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
