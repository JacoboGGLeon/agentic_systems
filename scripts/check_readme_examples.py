"""Run the introductory README offline; model responses are simulated, not live."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tutorials'))
from _offline import enforce_offline, blocked_attempts  # noqa: E402

enforce_offline()
from botocore.client import BaseClient  # noqa: E402

markdown = (ROOT / 'README.md').read_text()
blocks = re.findall(r'```python\n(.*?)\n```', markdown, re.S)
model = next(block for block in blocks if 'runtime = toolkit.runtime(' in block)
namespace = {}
log = io.StringIO()
with redirect_stdout(log):
    for block in blocks:
        if block != model:
            exec(compile(block, 'README:local', 'exec'), namespace)
toolkit = namespace['toolkit']
assert namespace['result'].data['difference'] == 5.0
assert namespace['checked'].data['verified'] is True
round_result = namespace['round_result']
assert len(round_result.data['outputs']) == 2
assert [row['previous_episodes'] for row in round_result.data['outputs']] == [0, 1]
assert round_result.data['summary']['state']['processed'] == 2
assert namespace['accepted'].ok
negative = toolkit.Eval('negative_control', unit=namespace['system'],
    cases=({'input': namespace['sample'], 'expected': {'ok': True}},),
    checks=(lambda result, case: {'ok': result.data['difference'] == 0.0},)).run()
assert not negative.ok
invalid = namespace['actuator'].run({'values': [1, 2, 3]})
assert not invalid.ok
calls = []


def simulated_converse(self, operation, params):
    assert operation == 'Converse'
    has_result = (not params.get('toolConfig', {}).get('tools')) or any(
        'toolResult' in block for message in params['messages'] for block in message['content'])
    text = ' '.join(block['text'] for message in params['messages']
                    if message['role'] == 'user' for block in message['content'] if 'text' in block)
    tool = 'profile_series' if 'describe' in text.lower() else 'compare_windows'
    calls.append(tool)
    content = [{'text': 'Recorded Tool result.'}] if has_result else [{'toolUse': {
        'toolUseId': 'offline-' + str(len(calls)), 'name': tool,
        'input': {'values': [10, 10, 15, 15]},
    }}]
    return {'output': {'message': {'role': 'assistant', 'content': content}},
            'stopReason': 'end_turn' if has_result else 'tool_use',
            'usage': {'inputTokens': 1, 'outputTokens': 1, 'totalTokens': 2},
            'metrics': {'latencyMs': 1}, 'ResponseMetadata': {'HTTPStatusCode': 200}}


config = {'AWS_REGION': 'us-east-1', 'AWS_ACCESS_KEY_ID': 'offline-placeholder',
          'AWS_SECRET_ACCESS_KEY': 'offline-placeholder', 'AWS_EC2_METADATA_DISABLED': 'true'}
with patch.dict(os.environ, config), patch.object(BaseClient, '_make_api_call', simulated_converse):
    exec(compile(model, 'README:model-declaration', 'exec'), namespace)
    for question, expected in [('Describe these observations: 10, 10, 15, 15.', 'profile_series'),
                               ('Compare these observations: 10, 10, 15, 15.', 'compare_windows')]:
        result = namespace['actor'].run(question)
        assert result.ok, [(r.errors, r.meta) for r in result.walk() if not r.ok]
        events = [e for run in result.walk() for e in run.tool_events]
        assert len(events) == 1 and events[0].name == expected and events[0].ok
        assert events[0].input == {'values': [10, 10, 15, 15]}
        assert result.check_invariants().ok
for result in [namespace['result'], namespace['checked'], round_result, namespace['accepted'], negative, invalid]:
    assert result.check_invariants().ok
for target in re.findall(r'\]\(([^)]+)\)', markdown):
    prefix = 'https://github.com/JacoboGGLeon/agentic_systems/'
    if target.startswith(prefix) and '/main/' in target:
        assert (ROOT / target.split('/main/', 1)[1].split('#')[0]).exists(), target
assert blocked_attempts() == 0
report = {'sdk_version': toolkit.__version__, 'readme_sha256': hashlib.sha256(markdown.encode()).hexdigest(),
          'python_blocks': len(blocks), 'local_output': log.getvalue(),
          'local_result_and_trajectory': 'PASS', 'environment_stop_and_memory': 'PASS',
          'negative_controls': 'PASS', 'native_two_tool_simulation': 'PASS',
          'simulated_converse_calls': len(calls), 'real_inference_requests': 0,
          'live_model_acceptance': 'NOT RUN'}
out = ROOT / '.tmp/readme-validation'
out.mkdir(parents=True, exist_ok=True)
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
