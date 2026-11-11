"""The primary export preserves compatibility, JSON, hierarchy and redaction."""
import json
from dataclasses import replace

import agentic_systems as toolkit


def test_evidence_preserves_nested_roundtrip_and_is_detached():
    child = toolkit.RunResult(data={'value': 42}, parent_execution_id='root')
    result = toolkit.RunResult(execution_id='root', data={'value': 42}, children=(child,))
    evidence = result.evidence()
    assert evidence == result.to_dict()
    assert evidence['children'][0] == child.evidence()
    restored = toolkit.RunResult(**json.loads(json.dumps(evidence)))
    assert restored.evidence() == evidence
    assert restored.check_invariants().ok
    evidence['data']['value'] = 0
    assert result.data['value'] == 42


def test_to_dict_delegates_to_primary_export(monkeypatch):
    monkeypatch.setattr(toolkit.RunResult, 'evidence', lambda self: {'primary': True})
    assert toolkit.RunResult().to_dict() == {'primary': True}


def test_failure_export_and_existing_secret_redaction():
    result = toolkit.RunResult(ok=False, errors=({'code': 'controlled'},),
                               meta={'api_key': 'do-not-export'})
    assert result.evidence() == result.to_dict()
    assert result.evidence()['status'] == 'failed'
    assert 'do-not-export' not in json.dumps(result.evidence())
    assert replace(result, ok=True, errors=()).evidence()['status'] == 'completed'


def test_five_independent_eval_recipes_accept_and_reject():
    import runpy
    from pathlib import Path
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'examples/eval_recipes.py'))
    assert len(namespace['evaluations']) == 5
