"""Evidence observer for offline harnesses; does not alter returned results."""
from functools import wraps
import json
from pathlib import Path
import agentic_systems as toolkit

_results = {}
_installed = False


def remember(result):
    if isinstance(result, toolkit.RunResult):
        _results[result.execution_id] = result
    return result


def install():
    global _installed
    if _installed:
        return
    _installed = True
    def probe(value: int) -> dict:
        return {'value': value}
    unit = toolkit.Agent('evidence_probe', toolkit.Action('identity', lambda data: data))
    captured = toolkit.Environment('probe', unit, records=({},)).compile()
    classes = {toolkit.Agent, toolkit.System, toolkit.Environment, toolkit.Eval,
               type(toolkit.tool(probe)), type(unit.compile()), type(captured)}
    for cls in classes:
        original = cls.run
        @wraps(original)
        def run(self, *args, __original=original, **kwargs):
            return remember(__original(self, *args, **kwargs))
        cls.run = run
        original_async = cls.arun
        @wraps(original_async)
        async def arun(self, *args, __original=original_async, **kwargs):
            return remember(await __original(self, *args, **kwargs))
        cls.arun = arun


def save(path, name):
    # Parent results already contain their descendant executions.
    descendants = {node.execution_id for result in _results.values() for node in result.walk()
                   if node.execution_id != result.execution_id}
    roots = [result for key, result in _results.items() if key not in descendants]
    rows = []
    for result in roots:
        try:
            lineage = result.lineage(name=name).to_dict()
            lineage_error = None
        except Exception as exc:
            lineage, lineage_error = None, {'type': type(exc).__name__, 'message': str(exc)}
        rows.append({'run_result': result.to_dict(), 'lineage_memory': lineage, 'lineage_error': lineage_error,
                     'invariants': result.check_invariants().to_dict()})
    payload = {'source': name, 'captured_boundaries': len(_results), 'root_results': len(rows),
               'scope': 'Observed SDK RunResult values; descendants retained inside parents. No fabricated results for configuration-only examples.',
               'results': rows}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return payload


def clear():
    _results.clear()
