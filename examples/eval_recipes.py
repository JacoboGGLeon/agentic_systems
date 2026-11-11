import pydantic
import agentic_systems as toolkit
from dataclasses import replace

def one_step(name, state_schema, operation):
    graph = toolkit.Graph(state_schema)
    graph.add_node('operation', operation)
    graph.add_edge(toolkit.START, 'operation')
    graph.add_edge('operation', toolkit.END)
    return toolkit.Agent(name, graph=graph)

def events(result):
    return [event for run in result.walk() for event in run.tool_events]

# 1. Result
class FeeState(pydantic.BaseModel):
    amount: int
    fee: int | None = None

@toolkit.tool
def calculate_fee(amount: int) -> dict:
    return {'fee': amount // 100}

fee_agent = one_step('fees', FeeState, calculate_fee)
eval1 = toolkit.Eval('correct_result', unit=fee_agent, cases=(
    {'input': {'amount': 5000},
     'expected': {'ok': True, 'data': {'amount': 5000, 'fee': 50}}},
))

# 2. Required Tool evidence
class SumState(pydantic.BaseModel):
    a: int
    b: int
    value: int | None = None

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {'value': a + b}

sum_agent = one_step('calculator', SumState, add)

def check_add(result, case):
    called = any(e.name == 'add' and e.ok and e.input == case['input']
                 for e in events(result))
    return {'ok': called and result.data.get('value') == 42}

eval2 = toolkit.Eval('required_tool', unit=sum_agent,
    cases=({'input': {'a': 19, 'b': 23}, 'expected': {'ok': True}},),
    checks=(check_add,))

# 3. Conditional route
class RiskState(pydantic.BaseModel):
    risk: int
    decision: str | None = None

@toolkit.tool
def manual_review(risk: int) -> dict:
    return {'decision': 'review'}

@toolkit.tool
def auto_approve(risk: int) -> dict:
    return {'decision': 'approve'}

def route(state):
    return 'manual' if state.risk >= 80 else 'automatic'

graph = toolkit.Graph(RiskState)
graph.add_node('manual', manual_review)
graph.add_node('automatic', auto_approve)
graph.add_conditional_edges(toolkit.START, route,
                            {'manual': 'manual', 'automatic': 'automatic'})
graph.add_edge('manual', toolkit.END)
graph.add_edge('automatic', toolkit.END)
risk_system = toolkit.System('risk', graph=graph)

def check_route(result, case):
    high = case['input']['risk'] >= 80
    wanted = 'manual_review' if high else 'auto_approve'
    forbidden = 'auto_approve' if high else 'manual_review'
    observed = events(result)
    return {'ok': any(e.name == wanted and e.ok for e in observed)
                  and not any(e.name == forbidden for e in observed)
                  and result.data.get('decision') == ('review' if high else 'approve')}

eval3 = toolkit.Eval('conditional_route', unit=risk_system,
    cases=({'input': {'risk': 90}, 'expected': {'ok': True}},
           {'input': {'risk': 20}, 'expected': {'ok': True}}),
    checks=(check_route,))

# 4. Expected failure
class OrderState(pydantic.BaseModel):
    sku: str
    available: bool | None = None
    confirmed: bool | None = None

@toolkit.tool
def inventory(sku: str) -> dict:
    raise RuntimeError('Controlled inventory failure')

@toolkit.tool
def confirm_order(sku: str) -> dict:
    return {'confirmed': True}

graph = toolkit.Graph(OrderState)
graph.add_node('inventory', inventory)
graph.add_node('confirm', confirm_order)
graph.add_edge(toolkit.START, 'inventory')
graph.add_edge('inventory', 'confirm')
graph.add_edge('confirm', toolkit.END)
order_system = toolkit.System('orders', graph=graph)

def check_failure(result, case):
    observed = events(result)
    return {'ok': (not result.ok) and result.status == 'failed'
            and bool(result.errors)
            and any(e.name == 'inventory' and not e.ok for e in observed)
            and not any(e.name == 'confirm_order' for e in observed)}

eval4 = toolkit.Eval('expected_failure', unit=order_system,
    cases=({'input': {'sku': 'A-1'}, 'expected': {'ok': False}},),
    checks=(check_failure,))

# 5. Episodes and stop
class EpisodeState(pydantic.BaseModel):
    amount: int
    previous: int
    total: int | None = None

@toolkit.tool
def accumulate(amount: int, previous: int) -> dict:
    return {'total': previous + amount}

graph = toolkit.Graph(EpisodeState)
graph.add_node('accumulate', accumulate)
graph.add_edge(toolkit.START, 'accumulate')
graph.add_edge('accumulate', toolkit.END)

def observe(record, state):
    return {'amount': record['amount'], 'previous': state['total']}

def update(state, record, result):
    return {'total': result.data['total']}

def stop(state, result):
    return state['total'] >= 5

environment = toolkit.Environment('ledger', graph=graph,
    records=({'amount': 2}, {'amount': 3}, {'amount': 100}),
    state={'total': 0}, observe=observe, update=update, stop=stop)

def check_episodes(result, case):
    totals = [output['total'] for output in result.data['outputs']]
    return {'ok': totals == [2, 5]
            and result.data['summary']['state']['total'] == 5}

eval5 = toolkit.Eval('episodes_and_stop', unit=environment,
    cases=({'input': {}, 'expected': {'ok': True}},),
    checks=(check_episodes,))

evaluations = [eval1, eval2, eval3, eval4, eval5]
for evaluation in evaluations:
    report = evaluation.run()
    assert report.ok, report.evidence()
    print(evaluation.name, 'PASS', len(report.data['cases']))

# Negative controls: every check must reject a deliberately false condition.
def reject(result, case):
    return {'ok': False}

for evaluation in evaluations:
    report = replace(evaluation, checks=(*evaluation.checks, reject)).run()
    assert not report.ok, report.evidence()
    print(evaluation.name, 'NEGATIVE CONTROL PASS')
