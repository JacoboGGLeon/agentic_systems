import agentic_systems as toolkit
from examples.api_walkthrough.example import observed_tool_data, runtime_step, approve


def test_accepts_known_transport_envelopes_without_editing_business_data():
    data = {'total': 200, 'status': 'approved'}
    assert observed_tool_data(data, 'approve') == data
    assert observed_tool_data({'data': data}, 'approve') == data
    envelope = {'kind': 'object', 'tool_name': 'approve', 'ok': True, 'data': data, 'meta': {'serializer': 'BedrockRuntime.ToolEnvelope.v1'}}
    assert observed_tool_data(envelope, 'approve') == data
    wrong = {**envelope, 'tool_name': 'other'}
    assert observed_tool_data(wrong, 'approve') == wrong
    failed = {**envelope, 'ok': False}
    assert observed_tool_data(failed, 'approve') == failed


def test_rejection_preserves_actor_evidence_and_usage(monkeypatch):
    original = toolkit.RunResult(data={'total': 999}, usage={'inference_requests': 1}, tool_events=(
        {'id': 'fixture-event', 'name': 'approve', 'input': {'total': 200}, 'output': {'total': 999, 'status': 'approved'}, 'ok': True},))
    monkeypatch.setattr(toolkit.Agent, 'run', lambda self, *args, **kwargs: original)
    boundary = runtime_step('approval', approve, toolkit.runtime(provider='python-runtime'), toolkit.framework('native'))
    result = boundary.flow.target({'total': 200})
    assert not result.ok and result.errors[-1]['code'] == 'business_boundary_rejected'
    assert result.tool_events == original.tool_events and result.usage == original.usage
    assert result.data == original.data and result.execution_id == original.execution_id
