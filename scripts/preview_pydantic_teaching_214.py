"""Generate review-only teaching diffs under revisions; never edit source files."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "revisions/2.1.4/pydantic-dev4/staged"


def dumped(node):
    return ast.Call(ast.Attribute(node, "model_dump", ast.Load()), [], [ast.keyword("exclude_unset", ast.Constant(True))])


class ModelAccess(ast.NodeTransformer):
    def __init__(self, name):
        self.name = name

    def visit_Subscript(self, node):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == self.name and isinstance(node.ctx, ast.Load):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                return ast.copy_location(ast.Attribute(node.value, node.slice.value, ast.Load()), node)
            return ast.copy_location(ast.Call(ast.Name("getattr", ast.Load()), [node.value, node.slice], []), node)
        return node

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == self.name and node.attr in {"get", "items", "keys", "values", "copy"}:
            return ast.copy_location(ast.Attribute(dumped(node.value), node.attr, node.ctx), node)
        return self.generic_visit(node)

    def visit_Dict(self, node):
        node = self.generic_visit(node)
        for i, (key, value) in enumerate(zip(node.keys, node.values)):
            if key is None and isinstance(value, ast.Name) and value.id == self.name:
                node.values[i] = dumped(value)
        return node


class Preview(ast.NodeTransformer):
    def __init__(self, nodes, pydantic_names):
        self.nodes = nodes
        self.pydantic_names = pydantic_names

    def visit_ImportFrom(self, node):
        if node.module in {"langgraph.graph", "langgraph.runtime", "langgraph.types"}:
            return None
        if node.module == "pydantic":
            return None
        if node.module == "typing_extensions":
            node.names = [n for n in node.names if n.name != "TypedDict"]
            return node if node.names else None
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.pydantic_names:
            return ast.copy_location(ast.Attribute(ast.Name("pydantic", ast.Load()), self.pydantic_names[node.id], ast.Load()), node)
        if isinstance(node.ctx, ast.Load) and node.id in {"StateGraph", "START", "END", "Runtime", "Command", "Send"}:
            return ast.copy_location(ast.Attribute(ast.Name("toolkit", ast.Load()), node.id, ast.Load()), node)
        return node

    def visit_ClassDef(self, node):
        if any(isinstance(b, ast.Name) and b.id == "TypedDict" for b in node.bases):
            optional = any(k.arg == "total" and isinstance(k.value, ast.Constant) and k.value.value is False for k in node.keywords)
            node.bases = [ast.Attribute(ast.Name("pydantic", ast.Load()), "BaseModel", ast.Load())]
            node.keywords = []
            if optional:
                for field in node.body:
                    if isinstance(field, ast.AnnAssign) and field.value is None and field.target.id not in {"value", "input", "subtotal"}:
                        if isinstance(field.annotation, ast.Subscript) and isinstance(field.annotation.value, ast.Name) and field.annotation.value.id == "Annotated":
                            field.value = ast.Call(ast.Attribute(ast.Name("pydantic", ast.Load()), "Field", ast.Load()), [], [ast.keyword("default_factory", ast.Name("list", ast.Load()))])
                        else:
                            field.annotation = ast.BinOp(field.annotation, ast.BitOr(), ast.Constant(None))
                            field.value = ast.Constant(None)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name == "show":
            return None
        decorated = any(isinstance(d, ast.Attribute) and d.attr == "tool" or isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "tool" for d in node.decorator_list)
        if node.name in self.nodes and node.args.args and not decorated:
            node = ModelAccess(node.args.args[0].arg).visit(node)
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"add_node", "add_conditional_edges"} and len(node.args) > 1 and isinstance(node.args[1], ast.Lambda):
            fn = node.args[1]
            if fn.args.args:
                fn.body = ModelAccess(fn.args.args[0].arg).visit(fn.body)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "Action":
            for kw in node.keywords:
                if kw.arg == "input" and isinstance(kw.value, ast.Lambda):
                    fn = kw.value
                    fn.body = ModelAccess(fn.args.args[0].arg).visit(fn.body)
        return self.generic_visit(node)

    def visit_Expr(self, node):
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "show":
            unit, _, expected = call.args
            name = "agent" if isinstance(unit, ast.Call) and isinstance(unit.func, ast.Attribute) and unit.func.attr == "Agent" else "system"
            code = f"{name} = {ast.unparse(unit)}\nresult = {name}.run({{'value': 2}})\nassert result.ok and result.data['value'] == {ast.unparse(expected)}\nassert result.check_invariants().ok\nprint(result.human_results())"
            return [self.visit(x) for x in ast.parse(code).body]
        return self.generic_visit(node)


def preview(sources):
    trees = [ast.parse(s) for s in sources]
    nodes = {n.args[1].id for tree in trees for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {"add_node", "add_conditional_edges"} and len(n.args) > 1 and isinstance(n.args[1], ast.Name)}
    pydantic_names = {n.asname or n.name: n.name for t in trees for imp in ast.walk(t) if isinstance(imp, ast.ImportFrom) and imp.module == "pydantic" for n in imp.names}
    result = [ast.unparse(ast.fix_missing_locations(Preview(nodes, pydantic_names).visit(t))).replace("2.1.4.dev3", "2.1.4.dev4") + "\n" for t in trees]
    if any("pydantic." in s for s in result) and not any("import pydantic\n" in s for s in result):
        i = next((i for i, s in enumerate(result) if "import agentic_systems as toolkit" in s), 0)
        tree = ast.parse(result[i])
        pos = 0
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
            pos = 1
        while pos < len(tree.body) and isinstance(tree.body[pos], ast.ImportFrom) and tree.body[pos].module == "__future__":
            pos += 1
        tree.body.insert(pos, ast.Import([ast.alias("pydantic")]))
        result[i] = ast.unparse(ast.fix_missing_locations(tree)) + "\n"
    return result


def main():
    paths = sorted(p for p in (ROOT / "examples").rglob("*.py") if p.name in {"example.py", "application.py", "resources.py", "system.py", "tools.py", "skills.py", "verification.py"} and not set(p.parts) & {"history", "build", "dist", "evidence", "tests", "__pycache__", "agentic_systems_studio"})
    paths += sorted((ROOT / "tutorials").rglob("*.ipynb")) + sorted(p for p in (ROOT / "examples").rglob("*.ipynb") if not set(p.parts) & {"history", "build", "dist", "evidence", "__pycache__"})
    rows = []
    for path in paths:
        rel = path.relative_to(ROOT)
        if path.suffix == ".py":
            text = preview([path.read_text(encoding="utf-8")])[0]
        else:
            nb = json.loads(path.read_text(encoding="utf-8"))
            cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
            for cell, code in zip(cells, preview(["".join(c["source"]) for c in cells])):
                cell.update(source=code.splitlines(keepends=True), outputs=[], execution_count=None)
            for cell in nb["cells"]:
                if cell["cell_type"] == "markdown":
                    cell["source"] = "".join(cell["source"]).replace("2.1.4.dev3", "2.1.4.dev4").replace("TypedDict", "modelo Pydantic").splitlines(keepends=True)
            nb["metadata"]["agentic_systems"] = {"version": "2.1.4.dev4", "orchestration": "langgraph", "state": "pydantic"}
            nb["metadata"].pop("validation_214", None)
            text = json.dumps(nb, ensure_ascii=False, indent=1) + "\n"
        target = STAGE / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        rows.append({"path": rel.as_posix(), "before_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "staged_sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    (STAGE.parent / "preview-manifest.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Generated {len(rows)} review-only files; active sources unchanged")


if __name__ == "__main__":
    main()
