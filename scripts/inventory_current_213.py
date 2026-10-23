"""Generate the supported 2.1.3 surface from the installed canonical SDK."""
from dataclasses import fields, is_dataclass
import inspect
import json
from pathlib import Path

import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
FAMILY = {
    "tool": ("01", "tool_contracts", "test_capabilities.py"), "Tool": ("01", "tool_contracts", "test_capabilities.py"),
    "skill": ("01", "portable_skills", "test_capabilities.py"), "Skill": ("01", "portable_skills", "test_capabilities.py"),
    "load_skill": ("01", "portable_skills", "test_capabilities.py"),
    "Action": ("02", "flow_semantics", "test_grammar.py"), "Agent": ("02,06,10", "agent_contracts", "test_grammar.py"),
    "System": ("03", "flow_semantics", "test_grammar.py"), "Sequence": ("02,03", "flow_semantics", "test_grammar.py"),
    "Parallel": ("02,03", "flow_semantics", "test_grammar.py"), "Graph": ("02,03", "flow_semantics", "test_grammar.py"),
    "Environment": ("04", "episode_memory", "test_grammar.py"), "Eval": ("05,10", "evaluation_checks", "test_grammar.py"),
    "Limits": ("07", "execution_lifecycle", "test_parameters.py"), "RunResult": ("07", "results_lineage", "test_capabilities.py"),
    "runtime": ("06", "provider_framework_conformance", "test_parameters.py"), "Runtime": ("06", "provider_framework_conformance", "test_parameters.py"),
    "framework": ("06", "provider_framework_conformance", "test_capabilities.py"), "Framework": ("06", "provider_framework_conformance", "test_capabilities.py"),
    "model_artifact": ("08", "model_serving", "test_capabilities.py"), "Artifact": ("08", "model_serving", "test_capabilities.py"),
    "model_server": ("08", "model_serving", "test_capabilities.py"), "Server": ("08", "model_serving", "test_capabilities.py"),
    "Compiled": ("07", "execution_lifecycle", "test_grammar.py"), "Captured": ("04,05", "episode_memory", "test_grammar.py"),
    "Lineage": ("07", "results_lineage", "test_capabilities.py"), "Event": ("07", "results_lineage", "test_parameters.py"),
    "Validation": ("07", "results_lineage", "test_capabilities.py"), "Endpoint": ("08", "model_serving", "test_capabilities.py"),
    "Health": ("08", "model_serving", "test_capabilities.py"),
    "CLI": ("00", "package_install", "test_distribution.py"),
}


def default(value):
    if value is inspect.Parameter.empty:
        return None
    if callable(value):
        return getattr(value, "__name__", type(value).__name__)
    if is_dataclass(value):
        return repr(value)
    return repr(value)


def params(value):
    return [{"name": p.name, "mode": p.kind.name, "required": p.default is inspect.Parameter.empty,
             "default": default(p.default), "annotation": str(p.annotation) if p.annotation is not inspect.Parameter.empty else None}
            for p in inspect.signature(value).parameters.values() if p.name not in {"self", "cls"}]


def main():
    @toolkit.tool
    def echo(value: int) -> dict:
        """Contract inventory fixture; never invoked."""
        return {"value": value}
    agent = toolkit.Agent("fixture", toolkit.Action("echo", echo))
    episode = toolkit.Environment("fixture", agent, ({"value": 1},))
    from agentic_systems._configuration import _Health
    objects = {"Tool": echo, "Skill": toolkit.skill(name="fixture", tools=[echo]),
        "Runtime": toolkit.runtime(provider="python-runtime"), "Framework": toolkit.framework("native"),
        "Artifact": toolkit.model_artifact("fixture/model"), "Server": toolkit.model_server(toolkit.model_artifact("fixture/model")),
        "Compiled": agent.compile(), "Captured": episode.compile(), "Lineage": toolkit.RunResult().lineage(),
        "Validation": toolkit.RunResult().check_invariants(),
        "Event": toolkit.RunResult(tool_events=({"id": "fixture", "name": "echo"},)).tool_events[0]}
    objects["Endpoint"] = objects["Server"].endpoint
    objects["Health"] = _Health("stopped", objects["Endpoint"], None)
    records = []
    for name in toolkit.__all__:
        if name == "__version__":
            continue
        value = getattr(toolkit, name)
        records.append({"id": name, "kind": "constructor" if inspect.isclass(value) else "function", "owner": name, "parameters": params(value)})
        if inspect.isclass(value):
            objects[name] = value
    for name, value in objects.items():
        cls = value if inspect.isclass(value) else type(value)
        data_fields = {f.name for f in fields(cls)} if is_dataclass(cls) else set()
        for member, descriptor in inspect.getmembers_static(cls):
            if member.startswith("_") or member in data_fields:
                continue
            if isinstance(descriptor, property):
                records.append({"id": name + "." + member, "owner": name, "kind": "property", "parameters": []})
            elif inspect.isfunction(descriptor):
                records.append({"id": name + "." + member, "owner": name, "kind": "method", "parameters": params(descriptor)})
        if is_dataclass(cls):
            for field in fields(cls):
                if not field.name.startswith("_") and not isinstance(inspect.getattr_static(cls, field.name, None), property):
                    records.append({"id": name + "." + field.name, "owner": name, "kind": "field", "annotation": str(field.type), "parameters": []})
    for name in ("version", "api", "doctor", "new"):
        records.append({"id": "CLI." + name, "owner": "CLI", "kind": "command",
                        "parameters": [{"name": "destination", "mode": "CLI_POSITIONAL", "required": True, "default": None, "annotation": "str"}] if name == "new" else []})
    ids = set()
    for record in records:
        assert record["id"] not in ids, record["id"]
        ids.add(record["id"])
        chapter, example, test = FAMILY[record["owner"]]
        record["tutorial_chapters"] = chapter
        record["example_ref"] = "examples/" + example + "/example.py"
        record["test_ref"] = "tests/v213/" + test
        record["evidence_ref"] = "revisions/2.1.3/closeout-evidence/manifest.json"
        record["scope"] = "offline contract; external providers configured/stubbed; serving lifecycle simulated"
    payload = {"version": toolkit.__version__, "public_api": toolkit.__all__, "records": records,
               "record_count": len(records), "parameter_count": sum(len(r["parameters"]) for r in records),
               "inference_requests": 0, "historical_inventory": "api_inventory_213/inventory.json",
               "coverage_note": "References identify contract families, not exhaustive proof of every parameter value or an upstream SDK capability."}
    (ROOT / "docs/api_213_contract.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = ["# Superficie efectiva 2.1.3", "", "Generada desde el SDK instalado con `scripts/inventory_current_213.py`.", "",
             "Incluye las firmas, campos y métodos soportados; los tipos retornados no tienen otro constructor público.", "",
             "| Entrada / miembro | Tipo | Parámetros | Tutorial | Ejemplo |", "|---|---|---|---|---|"]
    for r in records:
        signature = ", ".join(p["name"] + ("=" + p["default"] if not p["required"] else "") for p in r["parameters"])
        lines.append("| `" + r["id"] + "` | " + r["kind"] + " | `" + signature.replace("|", "\\|") + "` | " + r["tutorial_chapters"] + " | " + r["example_ref"] + " |")
    lines += ["", "[Tipos, defaults, modos de argumentos y enlaces de pruebas](api_213_contract.json).",
              "La evidencia de estas familias de contratos es offline. La [campaña externa](../revisions/2.1.3/framework-evidence/REPORT.md) documenta por separado sus modelos y escenarios live. GPU, IAM y opciones arbitrarias de SDK externos no quedan acreditados por este inventario.", ""]
    (ROOT / "docs/API_213_SURFACE.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"records": len(records), "parameters": payload["parameter_count"], "public_api": len(toolkit.__all__)}))


if __name__ == "__main__":
    main()
