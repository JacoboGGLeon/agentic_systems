"""Check the installed base API outside the checkout, without optional SDKs or inference."""
import importlib.metadata
import json
import os
from pathlib import Path
import sys

import agentic_systems as toolkit


def main():
    expected = os.environ.get('EXPECTED_VERSION') or os.environ.get('VERSION')
    assert expected, 'The release must declare its expected version'
    assert toolkit.__version__ == importlib.metadata.version('agentic-systems') == expected
    assert len(toolkit.__all__) == 18
    assert 'site-packages' in Path(toolkit.__file__).parts, 'Smoke must use the installed wheel'
    root = Path(__file__).resolve().parents[1]
    assert Path.cwd() != root and root not in Path.cwd().parents, 'Run outside the source checkout'
    assert not {'openai', 'agents', 'strands', 'langgraph', 'boto3'} & sys.modules.keys()
    worker = toolkit.Agent('smoke', toolkit.Action('sum', lambda data: {'total': sum(data['values'])}))
    result = worker.run({'values': [2, 3, 5]})
    assert result.ok and result.data == {'total': 10}, result.to_dict()
    assert result.check_invariants().ok, result.check_invariants().to_dict()
    assert all(node.usage.get('inference_requests', 0) == 0 for node in result.walk())
    assert json.loads(json.dumps(result.to_dict(), allow_nan=False))['data'] == {'total': 10}
    json.dumps(result.lineage(name='release-smoke').to_dict(), allow_nan=False)
    print(json.dumps({'version': expected, 'data': result.data, 'invariants_ok': True,
                      'installed_package': toolkit.__file__, 'inference_requests': 0}))


if __name__ == '__main__':
    main()
