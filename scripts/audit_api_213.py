"""Static API inventory of a frozen wheel. Never imports SDK code or runs it."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import csv
import hashlib
import inspect
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/api_inventory_213"
WHEEL = ROOT / "revisions/2.1.3/artifacts/agentic_systems-2.1.3-py3-none-any.whl"
ROOTS = {
    "tool": ("tools.decorators", "tool"), "skill": ("_factories", "skill"),
    "load_skill": ("_factories", "load_skill"),
    **{n: ("_grammar", n) for n in ("Action", "Agent", "System", "Sequence", "Parallel", "Graph", "Environment", "Eval", "Limits")},
    "RunResult": ("results", "RunResult"),
    **{n: ("_configuration", n) for n in ("runtime", "framework", "model_artifact", "model_server")},
}
FAMILIES = {
    "Tool": "tools", "Skill": "skills", "RuntimeConfig": "configuration",
    "SchedulerConfig": "configuration", "FrameworkConfig": "configuration",
    "AgentContract": "contracts", "RunPolicy": "contracts",
    "ModelArtifact": "serving", "VLLMServerSpec": "serving", "VLLMServer": "serving",
    "EndpointInfo": "serving", "ServerHealth": "serving",
    "RunResult": "results", "ToolEvent": "results", "LineageMemory": "results",
    "LineageStep": "results", "ValidationResult": "results", "ValidationIssue": "results",
    "Compiled": "execution", "_CompiledEnvironment": "execution", "_CompiledEval": "execution",
    **{n: "flows" for n in ("Unit", "Action", "Agent", "System", "Sequence", "Parallel", "Graph", "Environment", "Eval", "Limits")},
    "EvalReport": "evaluation-payload", "EvalCaseResult": "evaluation-payload",
    "EvalReproducibility": "evaluation-payload", "JudgeResult": "evaluation-payload",
    "JudgeFinding": "evaluation-payload", "JudgeRubric": "evaluation-payload",
}
TARGETS = {
    "tools": ("01", "tool_contracts"), "skills": ("01", "portable_skills"),
    "configuration": ("06", "provider_framework_conformance"),
    "contracts": ("06 + 10 (propuesto)", "agent_contracts"),
    "serving": ("08", "model_serving"), "results": ("07", "results_lineage"),
    "execution": ("07", "execution_lifecycle"), "flows": ("02–05 + 09", "order_fulfillment + flow_semantics"),
    "evaluation-payload": ("05 + 10 (propuesto)", "evaluation_checks"),
    "package": ("00", "package_install"),
}
KEEP_METHODS = {
    "Tool": {"run"}, "Skill": {"tools", "instructions"}, "RuntimeConfig": set(),
    "SchedulerConfig": set(), "FrameworkConfig": {"inspect"},
    "RunResult": {"walk", "to_dict", "lineage", "trace", "check_invariants"},
    "LineageMemory": {"explain", "to_prompt_context", "to_dict"},
    "LineageStep": set(), "ToolEvent": set(), "ValidationResult": {"to_dict"},
    "ValidationIssue": set(), "VLLMServer": {"inspect", "start", "health", "stop", "endpoint", "command"},
    "Compiled": {"run", "arun", "inspect"}, "_CompiledEnvironment": {"run"}, "_CompiledEval": {"run"},
    "Unit": {"run", "arun", "compile", "inspect"}, "Agent": {"run", "arun", "compile", "inspect"},
    "System": {"run", "arun", "compile", "inspect"}, "Environment": {"run", "compile"}, "Eval": {"run", "compile"},
}


def expr(node):
    return ast.unparse(node) if node is not None else None


def parameters(args):
    result = []
    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for index, (arg, default) in enumerate(zip(positional, defaults)):
        if arg.arg in {"self", "cls"}:
            continue
        result.append({"name": arg.arg, "type": expr(arg.annotation), "default": expr(default),
                       "required": default is None, "mode": "positional-only" if index < len(args.posonlyargs) else "positional-or-keyword"})
    if args.vararg:
        result.append({"name": args.vararg.arg, "type": expr(args.vararg.annotation), "default": None, "required": False, "mode": "var-positional"})
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        result.append({"name": arg.arg, "type": expr(arg.annotation), "default": expr(default), "required": default is None, "mode": "keyword-only"})
    if args.kwarg:
        result.append({"name": args.kwarg.arg, "type": expr(args.kwarg.annotation), "default": None, "required": False, "mode": "var-keyword"})
    return result


def field_required(value):
    if value is None or isinstance(value, ast.Constant) and value.value is Ellipsis:
        return True
    if isinstance(value, ast.Call) and expr(value.func) in {"Field", "field"}:
        defaults = [kw.value for kw in value.keywords if kw.arg in {"default", "default_factory"}]
        if defaults:
            return isinstance(defaults[0], ast.Constant) and defaults[0].value is Ellipsis
        if value.args:
            return isinstance(value.args[0], ast.Constant) and value.args[0].value is Ellipsis
        return True
    return False


def baseline_decision(name):
    if name in ROOTS or name == "__version__":
        return "conservar nombre; revisar firma", name
    replacement = {
        "agent": "Agent", "system": "System", "AgenticSystem": "System", "graph": "Graph",
        "environment": "Environment", "AgenticEnvironment": "Environment", "eval": "Eval",
        "Evaluator": "Eval", "run_eval": "Eval.run", "CompiledSystem": "unit.compile()",
        "SequentialPlan": "Sequence", "ParallelPlan": "Parallel", "AgenticGraph": "Graph",
        "GraphApp": "Graph", "agent_node": "Agent como nodo de Graph",
        "provider": "runtime", "scheduler": "runtime (actor) / Limits (flujo)",
        "Tool": "tool", "Skill": "skill", "LoadedSkill": "load_skill devuelve Skill",
        "toolset": "skill(tools=...)", "ToolSet": "skill(tools=...)",
        "RuntimeConfig": "runtime", "ModelProviderConfig": "runtime", "SchedulerConfig": "runtime",
        "FrameworkConfig": "framework", "ModelArtifact": "model_artifact", "ModelServer": "model_server",
        "VLLMServer": "model_server", "VLLMServerSpec": "model_server",
        "LineageMemory": "result.lineage()", "LineageStep": "result.lineage().steps",
        "lineage_memory": "result.lineage()", "AgentContract": "Agent.contract (diccionario cerrado)",
        "RunPolicy": "Agent.policy (diccionario cerrado)", "ContractPolicySpec": "declaración de Agent",
        "expect": "contract.tool_expectation (diccionario cerrado)",
        "JudgeRubric": "Eval.judge / contrato de juez propuestos", "JudgeResult": "Eval: resultado del juez",
        "EvalReport": "Eval.run().data", "build_agent_step_graph": "Environment(unit=Agent(...))",
        "EndpointInfo": "server.endpoint", "ServerHealth": "server.health()",
    }
    if name in replacement:
        return "retirar entrada duplicada; preservar capacidad", replacement[name]
    if name in {"resolve_auto_provider", "normalize_provider_priority", "AUTO_PROVIDER_ENV_VAR", "DEFAULT_AUTO_PROVIDER_PRIORITY"}:
        return "retirar comportamiento público", "selección explícita de runtime; sin fallback"
    if name.startswith(("show", "human_", "run_result_", "agent_output", "compose_result", "environment_summary", "eval_report_summary")) or name in {"final_answer", "normalize_output", "output_schema", "OutputSchema"}:
        return "retirar helper público; conservar representación", "RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación"
    return "hacer interno; sin alternativa pública paralela", "docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente"


def disposition(row):
    family = row["family"]
    owner = row.get("owner", "").split(".")[-1]
    member = row["name"]
    if row["exposure"] == "submodule":
        return "hacer interno", "Implementación incluida en el wheel; no constituye otra gramática soportada."
    if row["kind"] == "parameter":
        return "según propietario", "Decisión heredada de la firma; ver parent_id y excepciones de la propuesta."
    if row["kind"] == "field":
        if owner == "VLLMServer" and member == "spec":
            return "hacer interno", "No mutar el spec o sus secretos desde el recurso público."
        if owner == "System" and member == "skills":
            return "retirar del público", "Las capacidades pertenecen a Agents; System coordina unidades."
        if owner in {"Compiled", "_CompiledEnvironment", "_CompiledEval"}:
            return "hacer interno", "Estado del ejecutor; no modificar prepared/records_json/cases_json desde la aplicación."
        if owner == "RuntimeConfig" and member in {"provider_priority", "allow_python_fallback", "metadata", "scheduler"}:
            return "hacer interno", "Sin resolución automática ni segunda configuración de ejecución."
        if owner == "EndpointInfo" and member == "base_url":
            return "exponer como url", "Vista del endpoint: runtime(endpoint=server.endpoint.url); no endpoint.endpoint."
        if owner in {"RuntimeConfig", "ModelArtifact", "EndpointInfo"} and member in {"model_id", "region_name", "base_model_id", "tokenizer_id"}:
            return "unificar nombre", "Usar model/region/base_model/tokenizer/endpoint en configuración y vistas públicas."
        if owner == "Skill" and member in {"prompts", "contracts", "policy"}:
            return "sustituir o retirar", "instructions único; contratos ejecutables en Agent, sin políticas de Skill no aplicadas."
        if owner == "AgentContract" and member in {"must_call", "must_not_call", "require_no_unresolved_tool_failures"}:
            return "unificar", "tool_expectation y failure_policy son las fuentes canónicas."
        if owner == "RunPolicy" and member in {"max_turns", "max_tool_calls", "max_tokens"}:
            return "mover", "Un límite de actor se declara una vez en runtime, no también en policy."
        return "conservar dato documentado", "No implica conservar su constructor de implementación como entrada pública."
    if row["kind"] in {"method", "property", "protocol"}:
        if member in KEEP_METHODS.get(owner, set()):
            return "conservar", "Tiene una responsabilidad pública diferenciada; contrato y cobertura explícitos."
        if family == "serving" and owner in {"ModelArtifact", "EndpointInfo", "ServerHealth", "VLLMServerSpec"}:
            return "hacer interno", "Validadores y métodos de Pydantic no forman parte de la gramática."
        if family == "evaluation-payload":
            return "hacer interno", "La evaluación expone un RunResult y su payload, no otro runner."
        return "hacer interno o sustituir", "Ver decisiones de familia: evitar aliases, coerciones, mutación y formas alternativas."
    return "conservar" if row["exposure"] in {"root", "cli"} else "esquema relacionado; constructor interno" if row["exposure"] == "related-schema" else "tipo retornado; sin constructor alternativo", "Una sola entrada de construcción; los tipos auxiliares no se exportan por separado."


def extract(sources):
    classes = {}
    functions = {}
    modules = []
    for filename, source in sorted(sources.items()):
        if "/templates/" in filename:
            continue
        module = filename.removeprefix("agentic_systems/").removesuffix(".py").replace("/", ".")
        module = module.removesuffix(".__init__")
        tree = ast.parse(source.lstrip("\ufeff"))
        imports = []
        constants = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                imports.append({"module": "." * node.level + (node.module or ""), "names": [{"name": n.name, "as": n.asname} for n in node.names]})
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        constants.append({"name": target.id, "value": expr(node.value), "line": node.lineno})
            if isinstance(node, ast.ClassDef):
                classes[module + "." + node.name] = (module, filename, node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[module + "." + node.name] = (module, filename, node)
        modules.append({"module": module, "file": filename, "sha256": hashlib.sha256(source.encode()).hexdigest(), "imports": imports, "public_assignments": constants})
    short = {}
    for key, (_, _, node) in classes.items():
        short.setdefault(node.name, []).append(key)

    def resolve(name, module):
        local = module + "." + name
        return local if local in classes else short[name][0] if len(short.get(name, [])) == 1 else None

    def members(key, seen=()):
        if key in seen:
            return {}
        module, filename, node = classes[key]
        result = {}
        for base in node.bases:
            target = resolve(expr(base), module)
            if target:
                result.update(members(target, (*seen, key)))
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name) and not child.target.id.startswith("_"):
                if child.target.id != "model_config":
                    result[child.target.id] = ("field", filename, child)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and (not child.name.startswith("_") or child.name.startswith("__") and child.name.endswith("__")):
                kind = "property" if any(expr(d).endswith("property") for d in child.decorator_list) else "protocol" if child.name.startswith("__") else "method"
                result[child.name] = (kind, filename, child)
                if child.name == "__init__":
                    for statement in ast.walk(child):
                        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                            for target in targets:
                                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self" and not target.attr.startswith("_"):
                                    result.setdefault(target.attr, ("instance-field", filename, statement))
        return result

    reachable = {k for k, (_, _, n) in classes.items() if n.name in FAMILIES}
    # Recursively include project-owned types referenced by fields, signatures and bases.
    changed = True
    while changed:
        changed = False
        for key in list(reachable):
            module, _, node = classes[key]
            annotations = [*node.bases]
            for child in ast.walk(node):
                if isinstance(child, ast.arg) and child.annotation:
                    annotations.append(child.annotation)
                if isinstance(child, ast.AnnAssign):
                    annotations.append(child.annotation)
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.returns:
                    annotations.append(child.returns)
            for annotation in annotations:
                for name in re.findall(r"\b[A-Za-z_]\w*\b", expr(annotation)):
                    target = resolve(name, module)
                    if target and target not in reachable:
                        reachable.add(target)
                        changed = True
    rows = []

    def add(row):
        row.setdefault("family", "package")
        row["decision"], row["rationale"] = disposition(row)
        row["tutorial_target"], row["example_target"] = TARGETS.get(row["family"], TARGETS["package"])
        rows.append(row)
        for p in row.get("parameters", []):
            child = {"id": row["id"] + "/" + p["name"], "name": p["name"], "owner": row["id"], "parent_id": row["id"],
                     "kind": "parameter", "family": row["family"], "exposure": row["exposure"], "source": row["source"], "line": row["line"], **p}
            child["decision"] = row["decision"]
            child["rationale"] = "Sigue al propietario; las excepciones canónicas se enumeran en parameter_decisions.json."
            child["tutorial_target"], child["example_target"] = row["tutorial_target"], row["example_target"]
            rows.append(child)

    for public, (module, name) in ROOTS.items():
        key = module + "." + name
        if key in functions:
            _, filename, node = functions[key]
            ps = parameters(node.args)
            add({"id": "toolkit." + public, "name": public, "owner": "toolkit", "kind": "function", "exposure": "root",
                 "family": {"tool": "tools", "skill": "skills", "load_skill": "skills", "runtime": "configuration", "framework": "configuration", "model_artifact": "serving", "model_server": "serving"}[public],
                 "source": filename, "line": node.lineno, "signature": "(" + ast.unparse(node.args) + ")", "parameters": ps,
                 "return_annotation": expr(node.returns)})
    version_node = next(n for n in ast.parse(sources["agentic_systems/__init__.py"]).body
                        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets))
    add({"id": "toolkit.__version__", "name": "__version__", "owner": "toolkit", "kind": "constant", "exposure": "root", "source": "agentic_systems/__init__.py", "line": version_node.lineno, "value": ast.literal_eval(version_node.value)})
    for key, (module, filename, node) in sorted(classes.items()):
        if node.name.startswith("_") and key not in reachable:
            continue
        family = FAMILIES.get(node.name, "package")
        isroot = node.name in ROOTS and ROOTS[node.name] == (module, node.name)
        exposure = "root" if isroot else "related-schema" if family in {"contracts", "evaluation-payload"} else "reachable" if key in reachable else "submodule"
        owner = "toolkit." + node.name if isroot else key
        ms = members(key)
        fields = []
        for member, (kind, _, child) in ms.items():
            if kind == "field" and not (isinstance(child.value, ast.Call) and any(kw.arg == "init" and expr(kw.value) == "False" for kw in child.value.keywords)):
                dataclass = any("dataclass" in expr(d) for d in node.decorator_list)
                fields.append({"name": member, "type": expr(child.annotation), "default": expr(child.value), "required": field_required(child.value), "mode": "positional-or-keyword" if dataclass else "keyword-only"})
        init = ms.get("__init__")
        ps = parameters(init[2].args) if init else fields
        add({"id": owner, "name": node.name, "owner": module, "kind": "class", "exposure": exposure, "family": family,
             "source": filename, "line": node.lineno, "bases": [expr(b) for b in node.bases],
             "signature": "(" + ast.unparse(init[2].args) + ")" if init else "(" + ("*, " if fields and fields[0]["mode"] == "keyword-only" else "") + ", ".join(p["name"] + (": " + p["type"] if p["type"] else "") + (" = " + p["default"] if not p["required"] else "") for p in fields) + ")",
             "parameters": ps, "constructor_note": "Defaults of Field/field are preserved as source expressions, not evaluated."})
        for member, (kind, declared_file, child) in ms.items():
            if member == "__init__":
                continue
            row = {"id": owner + "." + member, "name": member, "owner": owner, "kind": "field" if kind == "instance-field" else kind,
                   "family": family, "exposure": exposure, "source": declared_file, "line": child.lineno,
                   "inherited": declared_file != filename or child not in node.body}
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                row.update(signature="(" + ast.unparse(child.args) + ")", parameters=parameters(child.args), return_annotation=expr(child.returns), decorators=[expr(d) for d in child.decorator_list])
            else:
                row.update(type=expr(child.annotation) if isinstance(child, ast.AnnAssign) else None, default=expr(child.value))
            add(row)
    # Include non-root public module functions as accidental alternate entrypoints.
    for key, (_, filename, node) in sorted(functions.items()):
        if node.name.startswith("_") or key in {m + "." + n for m, n in ROOTS.values()}:
            continue
        add({"id": key, "name": node.name, "owner": key.rsplit(".", 1)[0], "kind": "function", "exposure": "submodule", "source": filename,
             "line": node.lineno, "signature": "(" + ast.unparse(node.args) + ")", "parameters": parameters(node.args), "return_annotation": expr(node.returns)})
    # Resolve the two public **kwargs boundaries whose effective signatures are known.
    for parent, target, excluded in (
        ("toolkit.model_server", "serving.vllm.vllm_server_spec", {"model"}),
        ("toolkit.RunResult.lineage", "lineage.LineageMemory.from_run_result", {"result"}),
    ):
        original = next(r for r in rows if r["id"] == target)
        parent_row = next(r for r in rows if r["id"] == parent)
        for p in original["parameters"]:
            if p["name"] not in excluded:
                add({"id": parent + "/" + p["name"], "name": p["name"], "owner": parent, "parent_id": parent,
                     "kind": "parameter", "family": parent_row["family"], "exposure": parent_row["exposure"],
                     "source": original["source"], "line": original["line"], "forwarded_from": target,
                     **p, "mode": "effective-keyword-via-kwargs"})
    for name in ("version", "api", "doctor", "new"):
        cli_node = next(n for n in ast.walk(ast.parse(sources["agentic_systems/cli.py"]))
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_parser"
                        and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == name)
        ps = [{"name": "destination", "type": "str", "default": None, "required": True, "mode": "cli-positional"}] if name == "new" else []
        add({"id": "cli." + name, "name": name, "owner": "cli", "kind": "command", "exposure": "cli", "family": "package",
             "source": "agentic_systems/cli.py", "line": cli_node.lineno, "signature": "agentic-systems " + name + (" destination" if ps else ""), "parameters": ps})
    return rows, modules


def coverage():
    result = {"tutorials": [], "examples": []}
    paths = [("tutorials", p) for p in sorted((ROOT / "tutorials").glob("[0-9][0-9]_*.ipynb"))]
    paths += [("examples", p) for p in sorted((ROOT / "examples/order_fulfillment").glob("*.py"))]
    for category, path in paths:
        cells = [(i, "".join(c["source"])) for i, c in enumerate(json.loads(path.read_text(encoding="utf-8"))["cells"]) if c["cell_type"] == "code"] if path.suffix == ".ipynb" else [(None, path.read_text(encoding="utf-8"))]
        for cell, source in cells:
            tree = ast.parse(source)
            imports = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module == "agentic_systems":
                    imports.update({a.asname or a.name: a.name for a in n.names})
            calls = []
            refs = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "toolkit":
                    refs.add(n.attr)
                if isinstance(n, ast.Call):
                    target = expr(n.func)
                    public = imports.get(target) or target.removeprefix("toolkit.") if target in imports or target.startswith("toolkit.") else None
                    if public in ROOTS or isinstance(n.func, ast.Attribute):
                        calls.append({"expression": target, "root_symbol": public if public in ROOTS else None,
                                      "keyword_arguments": [k.arg or "**mapping" for k in n.keywords], "positional_arguments": len(n.args), "line": n.lineno})
                if isinstance(n, ast.Name) and n.id in imports:
                    refs.add(imports[n.id])
            result[category].append({"path": path.relative_to(ROOT).as_posix(), "cell": cell,
                                     "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "root_references": sorted(refs), "calls": calls})
    result["interpretation"] = "Static code references/calls, not proof of execution, assertions or semantic acceptance. Method receivers are not resolved; method-name hits can be ambiguous. Historical examples excluded."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with zipfile.ZipFile(WHEEL) as archive:
        sources = {n: archive.read(n).decode("utf-8") for n in archive.namelist() if n.startswith("agentic_systems/") and n.endswith(".py")}
    rows, modules = extract(sources)
    api = ast.parse(sources["agentic_systems/api.py"])
    public = ast.literal_eval(next(n.value for n in api.body if isinstance(n, ast.Assign)))
    assert len(public) == 18
    assert set(public) == {r["name"] for r in rows if r["exposure"] == "root" and r["kind"] != "parameter" and r["owner"] in {"toolkit", "_grammar", "results"}}
    rules_path = OUT / "parameter_decisions.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    indexed = {r["id"]: r for r in rows}
    assert len(indexed) == len(rows), "Duplicate inventory ID"
    for row in rows:
        if row["kind"] == "parameter":
            if row.get("parent_id") in indexed:
                parent = indexed[row["parent_id"]]
                row["decision"], row["rationale"] = parent["decision"], parent["rationale"]
            corresponding_field = indexed.get(row["parent_id"] + "." + row["name"])
            if corresponding_field and corresponding_field["kind"] == "field":
                row["decision"], row["rationale"] = corresponding_field["decision"], corresponding_field["rationale"]
    for rule in rules["decisions"]:
        assert rule["id"] in indexed, rule["id"]
        indexed[rule["id"]].update({k: v for k, v in rule.items() if k != "id"})
    old_tree = ast.parse((ROOT / "src/agentic_systems/api.py").read_text(encoding="utf-8"))
    old = ast.literal_eval(next(n.value for n in old_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "STABLE_API" for t in n.targets)))
    migration = [{"symbol": n, "decision": baseline_decision(n)[0], "destination": baseline_decision(n)[1]} for n in old]
    # Snapshot dependency inheritance without importing any Agentic Systems module.
    from pydantic import BaseModel
    inherited = []
    for name, value in inspect.getmembers_static(BaseModel):
        if name.startswith("_"):
            continue
        target = value.__func__ if isinstance(value, (classmethod, staticmethod)) else value
        try:
            signature = str(inspect.signature(target)) if callable(target) else None
        except (TypeError, ValueError):
            signature = "not introspectable"
        inherited.append({"name": name, "kind": "callable" if callable(target) else "attribute", "signature": signature,
                          "decision": "dependency detail; not supported grammar", "rationale": "Keep validation internals private; do not count inherited Pydantic methods as SDK entrypoints."})
    counts = {"rows": len(rows), "by_exposure": dict(Counter(r["exposure"] for r in rows)), "by_kind": dict(Counter(r["kind"] for r in rows)),
              "candidate_root_exports": len(public), "baseline_stable_exports": len(old), "modules": len(modules), "pydantic_public_members": len(inherited)}
    inventory = {"schema": "agentic-systems.static-api-inventory.v1", "date": "2026-10-22", "status": "proposal-only; runtime unchanged",
                 "wheel": WHEEL.relative_to(ROOT).as_posix(), "wheel_sha256": hashlib.sha256(WHEEL.read_bytes()).hexdigest(),
                 "inference_requests": 0, "method": "AST of frozen wheel; explicit return/payload type seeds and annotation closure; no SDK import, no callbacks, no server launch",
                 "limitations": ["Dynamic attributes on SDK/provider native objects are not statically enumerable; native handles should become private.",
                                 "Open mappings (framework SDK options, metadata, JSON payloads) are recorded as mappings, not a promise to enumerate upstream APIs.",
                                 "Generated dataclass/Pydantic constructors list declared and inherited fields; Field expressions retain source semantics.",
                                 "Submodule inventory includes implementation definitions, inherited members and imports; static presence does not imply supported public API."],
                 "counts": counts, "public_api": list(public), "rows": rows, "modules": modules, "pydantic_base_model_surface": inherited,
                 "baseline_212_crosswalk": migration, "coverage": coverage()}
    outputs = {OUT / "inventory.json": json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"}
    import io
    stream = io.StringIO(newline="")
    columns = ["id", "kind", "exposure", "family", "signature", "type", "default", "required", "mode", "source", "line", "inherited", "decision", "rationale", "tutorial_target", "example_target"]
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    outputs[OUT / "inventory.csv"] = stream.getvalue()
    cov = inventory["coverage"]
    coverage_md = ["# Apariciones actuales de los 18 exports", "", "Referencias estáticas de código; no acreditan ejecución ni cobertura de cada parámetro.", "",
                   "09 integra la aplicación por importación; sus usos indirectos aparecen en las fuentes del ejemplo, no como llamadas directas del notebook.", "",
                   "| Palabra | Tutoriales: referencias directas | Ejemplo 2.1.3: archivos |", "|---|---|---|"]
    for name in public:
        tutorial_refs = sorted({Path(r["path"]).name for r in cov["tutorials"] if name in r["root_references"]})
        example_refs = sorted({Path(r["path"]).name for r in cov["examples"] if name in r["root_references"]})
        coverage_md.append("| `" + name + "` | " + ", ".join(tutorial_refs or ["sin referencia directa"]) + " | " + ", ".join(example_refs or ["sin referencia directa"]) + " |")
    coverage_md += ["", "[Plan de cobertura por métodos, parámetros y casos](../API_213_COVERAGE_PLAN.md).", ""]
    outputs[OUT / "COVERAGE.md"] = "\n".join(coverage_md)
    md = ["# Inventario completo observado — candidata 2.1.3", "", "Generado con `python scripts/audit_api_213.py`; propuesta, no implementación.", "",
          "Wheel SHA-256: `" + inventory["wheel_sha256"] + "`.", "", "```json", json.dumps(counts, indent=2), "```", "",
          "Cada parámetro tiene su fila en [inventory.csv](inventory.csv) y su valor/tipo/modo en [inventory.json](inventory.json).",
          "Las firmas siguientes incluyen métodos heredados propios y propiedades. Las de tipos no exportados son superficie accesible, no constructores que debamos enseñar.", "",
          "[Decisión de diseño](../API_213_DISPOSITION.md). [Cobertura propuesta](../API_213_COVERAGE_PLAN.md).", ""]
    for family in sorted({r["family"] for r in rows if r["exposure"] != "submodule"}):
        md += ["## " + family, "", "| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |", "|---|---|---|---|"]
        for r in rows:
            if r["family"] == family and r["exposure"] != "submodule" and r["kind"] != "parameter":
                value = r.get("signature") or ((r.get("type") or "Any") + " = " + (r.get("default") or "requerido"))
                md.append("| `" + r["id"] + "` | " + r["kind"] + " | `" + value.replace("|", "\\|").replace("\n", " ") + "` | " + r["decision"] + " |")
        md.append("")
    md += ["## Entradas estables de 2.1.2", "", "Esta tabla es un cruce de nombres; no conserva firmas ni promete compatibilidad.", "", "| Entrada anterior | Decisión | Destino |", "|---|---|---|"]
    md += ["| `" + r["symbol"] + "` | " + r["decision"] + " | " + r["destination"] + " |" for r in migration]
    md += ["", "## Límites del inventario", ""] + ["- " + s for s in inventory["limitations"]]
    md += ["", "Los métodos heredados de Pydantic y todos los símbolos de submódulos quedan enumerados en el JSON. No se ocultan de este inventario aunque se proponga retirarlos de la superficie pública.", ""]
    outputs[OUT / "INVENTORY.md"] = "\n".join(md)
    for path, content in outputs.items():
        if args.check:
            assert path.read_text(encoding="utf-8") == content, path
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
