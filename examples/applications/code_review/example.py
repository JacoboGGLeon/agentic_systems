"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def inspect_source(input: dict) -> dict:
    import ast
    tree = ast.parse(input["source"])
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    return {"syntax_ok": True, "functions": len(functions),
            "missing_return_annotations": [node.name for node in functions if node.returns is None]}


capability = toolkit.skill(name="inspect_source", tools=(inspect_source,))
worker = toolkit.Agent("worker", toolkit.Action("inspect_source", "inspect_source"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'source': 'def total(values):\n    return sum(values)\n'}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'syntax_ok': True, 'functions': 1, 'missing_return_annotations': ['total']}, result.to_dict()
    return result
