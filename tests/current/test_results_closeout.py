"""Close observable serialization and bounded presentation contracts."""
import json
import pytest
from pydantic import BaseModel, field_serializer
from agentic_systems import RunResult
from agentic_systems._results import _Event, _Lineage, _json, _preview


def test_json_uses_model_json_serialization():
    class Payload(BaseModel):
        value: int
        @field_serializer('value')
        def serialize(self, value, info):
            return str(value) if info.mode == 'json' else value
    assert _json(Payload(value=4)) == {'value': '4'}


@pytest.mark.parametrize('value,message', [({1: 2}, 'JSON keys must be strings'), (object(), 'Expected finite JSON data')])
def test_json_exact_errors(value, message):
    with pytest.raises(TypeError) as caught:
        _json(value)
    assert str(caught.value) == message


def test_preview_compact_unicode_encoding():
    assert _preview({'ñ': [1, 2]}, max_chars=8) == {'preview': '{"ñ":[1,', 'omitted': True}


def test_saved_snapshots_detach_resume_and_sequence_fields():
    interrupts = [{'question': 'approve'}]
    continuation = {'id': 'resume'}
    run = RunResult(status='paused', interrupts=interrupts, continuation=continuation,
                    messages=[{'role': 'user'}], raw_responses=[{'response': 1}])
    interrupts[0]['question'] = 'changed'
    continuation['id'] = 'changed'
    assert run.interrupts == ({'question': 'approve'},)
    assert run.continuation == {'id': 'resume'}
    assert run.messages == ({'role': 'user'},)
    assert run.raw_responses == ({'response': 1},)


def line(steps=(), answer='', execution_id='r'):
    return _Lineage('audit', '', '', answer, True, tuple(steps), {}, None, (), {}, execution_id=execution_id)


def test_missing_evidence_is_not_failure():
    steps = [{'step_id': str(i), 'title': 't', 'summary': 's'} for i in range(13)]
    assert line(steps).render().splitlines()[-1] == '1 more steps; retrieve evidence by execution_id.'
    assert json.loads(line(steps).to_prompt_context(max_chars=4000))['failed_steps'] == 0


def test_prompt_envelope_exact_budgets():
    envelope = '{"ok":true,"steps":[],"omitted_steps":0,"failed_steps":0}'
    assert line().to_prompt_context(max_chars=len(envelope)) == envelope
    with pytest.raises(ValueError) as caught:
        line().to_prompt_context(max_chars=1)
    assert str(caught.value) == 'Context budget is too small for a valid lineage envelope'
    for size in [True, 0, -1]:
        with pytest.raises(ValueError) as caught:
            line().to_prompt_context(max_chars=size)
        assert str(caught.value) == 'max_chars must be positive'
    with_id = envelope[:-1] + ',"execution_id":"r"}'
    assert line().to_prompt_context(max_chars=len(with_id)) == with_id
    step = {'step_id': 's', 'evidence': {'ok': True}}
    expected = {'ok': True, 'steps': [step], 'omitted_steps': 0, 'failed_steps': 0, 'execution_id': 'r'}
    encoded = json.dumps(expected, separators=(',', ':'))
    assert line([step]).to_prompt_context(max_chars=len(encoded)) == encoded


def test_prompt_default_budget_is_1600():
    steps = [{'step_id': 'large', 'evidence': {'ok': True}, 'text': 'x' * 1450}]
    value = line(steps, answer='x' * 120)
    assert value.to_prompt_context() == value.to_prompt_context(max_chars=1600)
    # Locate an exact default-budget boundary using answer length.
    for size in range(1400, 1700):
        candidate = line(answer='x' * size)
        text = candidate.to_prompt_context(max_chars=1601)
        if len(text) == 1601:
            assert candidate.to_prompt_context() != text
            break
    else:
        pytest.fail('No exact boundary fixture')


def test_lineage_successful_tool_and_retries_and_unicode():
    run = RunResult(data={'ñ': 'sí'}, meta={'input': {'ñ': 'sí'}, 'scheduler_execution': {'attempt_history': [
        {'number': 1, 'status': 'completed'}, {'number': 2, 'status': 'completed'}]}}, tool_events=(_Event('e', 'tool'),))
    result = run.lineage()
    assert result.steps[-1]['summary'] == 'completed'
    assert [s['kind'] for s in result.steps] == ['execution', 'attempt', 'attempt', 'tool']
    assert result.question == '{"ñ": "sí"}' and result.answer == '{"ñ": "sí"}'
    assert RunResult().trace()['omitted_steps'] == 0


@pytest.mark.parametrize('kind', ['environment', 'eval'])
def test_empty_business_inputs_and_internal_owners(kind):
    run = RunResult(meta={'kind': kind})
    assert ('Input: {"records_observed":[]}' if kind == 'environment' else 'Input: {"cases_executed":[]}') in run.human_results()
    child = RunResult(meta={'kind': 'agent', 'owner_kind': kind, 'next': 'hidden'})
    assert RunResult(children=(child,)).human_results().splitlines()[-1] == '- No business operation recorded.'


def test_human_default_and_paused_headers():
    assert RunResult().human_results().splitlines()[0] == 'run: COMPLETED'
    run = RunResult(status='paused', interrupts=[{'q': 'approve'}], continuation={'id': 'r'})
    assert run.human_results().splitlines()[0] == 'run: PAUSED'
    assert run.human_results().splitlines()[4] == 'Awaiting resume; execution is not complete.'


@pytest.mark.parametrize('kind', ['agent', 'failure', 'tool', 'attempt', 'decision'])
def test_human_failed_operations_have_priority(kind):
    good = RunResult(meta={'kind': 'agent', 'name': 'good'})
    if kind == 'agent':
        run = RunResult(children=(good, RunResult(ok=False, meta={'kind': 'agent', 'name': 'bad'})))
        expected = '- Agent bad: failed'
    elif kind == 'failure':
        run = RunResult(children=(good, RunResult(ok=False, meta={'name': 'bad'})))
        expected = '- Failure bad: failed'
    elif kind == 'tool':
        run = RunResult(tool_events=(_Event('g', 'good'), _Event('b', 'bad', ok=False, error={'code': 'bad'})))
        expected = '- Tool bad: failed -> {"code":"bad"}'
    elif kind == 'attempt':
        run = RunResult(meta={'scheduler_execution': {'attempt_history': [{'number': 1, 'status': 'completed'}, {'number': 2, 'status': 'failed'}]}})
        expected = '- Attempt 2: failed'
    else:
        run = RunResult(children=(RunResult(meta={'next': 'good'}), RunResult(ok=False, meta={'name': 'bad'})))
        expected = '- Failure bad: failed'
    assert [s for s in run.human_results(max_steps=1).splitlines() if s.startswith('- ')] == [expected]


def test_human_bounded_operation_allocation_exact_boundary():
    run = RunResult(execution_id='r' * 30, children=(RunResult(meta={'kind': 'agent', 'name': 'a' * 80}),))
    header = 'run: COMPLETED\nExecution: ' + 'r' * 30 + '\nInput: not recorded\nOutput: {}\nProcess:'
    operation = '- Agent ' + 'a' * 80 + ': completed'
    boundary = sum(len(s) + 1 for s in header.splitlines()) + len(operation) + 80
    for budget in [boundary - 1, boundary, boundary + 1]:
        report = run.human_results(max_chars=budget)
        assert (operation in report) == (budget >= boundary)


def test_human_final_clip_and_default_budget():
    run = RunResult(execution_id='r' * 80, meta={'name': 'n' * 80, 'input': 'x' * 3000}, data={'x': 'x' * 3000}, errors=({'error': 'x' * 3000},))
    for budget in [256, 257, 300]:
        text = run.human_results(max_chars=budget)
        assert len(text) == budget and text.endswith('…')
    assert run.human_results() == run.human_results(max_chars=4000)
    assert run.human_results(max_chars=5000).splitlines()[2] == 'Input: ' + '"' + 'x' * 498 + '…'


def test_human_exact_final_budget_does_not_replace_last_character():
    run = RunResult(execution_id='r' * 80, meta={'name': 'n' * 80, 'input': 'x' * 9})
    text = run.human_results(max_chars=256)
    assert len(text) == 256
    assert text.endswith('- No business operation recorded.')


def test_human_default_4000_budget_excludes_operation_requiring_4001():
    run = RunResult(execution_id='r', tool_events=(_Event('e', 't' * 3829),))
    assert run.human_results() == run.human_results(max_chars=4000)
    assert '1 operations omitted; inspect lineage for full evidence.' in run.human_results()
    assert '- Tool ' in run.human_results(max_chars=4001)
