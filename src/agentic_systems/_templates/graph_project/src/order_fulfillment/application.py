"""A refund workflow: Python operators, optional real language interpretation."""
import pydantic
import agentic_systems as toolkit
CASE = {'order_id': ' R-17 ', 'amount': 240, 'expected_items': ['adapter', 'sensor'], 'received_items': ['adapter'], 'customer_note': 'La caja llegó sellada. Encontré el adaptador; el sensor del albarán no venía. Quiero devolver todo.'}
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['order_id', 'amount', 'total_units', 'missing_units', 'reason', 'sources'], 'properties': {'order_id': {'type': 'string'}, 'amount': {'type': 'integer'}, 'total_units': {'type': 'integer', 'minimum': 1}, 'missing_units': {'type': 'integer', 'minimum': 0}, 'reason': {'type': 'string', 'minLength': 5}, 'sources': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1}}}

@toolkit.tool
def normalize(order_id: str, amount: int, expected_items: list, received_items: list, customer_note: str) -> dict:
    """Normalize identifiers and preserve the evidence, without interpretation."""
    if amount < 0 or not expected_items:
        raise ValueError('A case needs nonnegative amount and an itemized packing slip')
    return {'order_id': order_id.strip(), 'amount': amount, 'expected_items': expected_items, 'received_items': received_items, 'customer_note': customer_note}

@toolkit.tool
def classify(order_id: str, amount: int, expected_items: list, received_items: list, customer_note: str) -> dict:
    """Deterministic operator for structured item evidence; no language understanding."""
    return {'order_id': order_id, 'amount': amount, 'total_units': len(expected_items), 'missing_units': len(set(expected_items) - set(received_items)), 'reason': 'Difference between packing slip and received item list', 'sources': ['packing-slip', 'customer-report']}

@toolkit.tool
def price(order_id: str, amount: int, total_units: int, missing_units: int, reason: str, sources: list) -> dict:
    """Compute money in integer units; never delegate arithmetic to a model."""
    if not 0 <= missing_units <= total_units or total_units < 1:
        raise ValueError('Inconsistent quantities')
    return {'order_id': order_id, 'refund': amount * missing_units // total_units}

@toolkit.tool
def policy(order_id: str, amount: int, total_units: int, missing_units: int, reason: str, sources: list, *, context: toolkit.Context) -> dict:
    """Use semantic domain Context and retain the classifier's evidence."""
    return {'currency': context.data['currency'], 'review_threshold': context.data['review_threshold'], 'reason': reason, 'sources': sources, 'missing_units': missing_units, 'previous_episodes': len(context.episodes)}

class RefundState(pydantic.BaseModel):
    order_id: str | None = None
    amount: int | None = None
    expected_items: list | None = None
    received_items: list | None = None
    customer_note: str | None = None
    total_units: int | None = None
    missing_units: int | None = None
    reason: str | None = None
    sources: list | None = None
    refund: int | None = None
    currency: str | None = None
    review_threshold: int | None = None
    previous_episodes: int | None = None
    needs_review: bool | None = None
    status: str | None = None

class RefundOutput(pydantic.BaseModel):
    order_id: str
    refund: int
    currency: str
    missing_units: int
    reason: str
    sources: list
    previous_episodes: int
    status: str

def tool_agent(name, operation, *, skills=()):
    graph = toolkit.Graph(RefundState)
    graph.add_node(name, operation)
    graph.add_edge(toolkit.START, name)
    graph.add_edge(name, toolkit.END)
    return toolkit.Agent(name, graph=graph, skills=skills)

def build_system(framework='native', *, reasoner=None, interactive=False):
    domain = toolkit.Context({'currency': 'MXN', 'review_threshold': 100, 'refund_policy': "Refund only missing items proportionally; the customer's demand is not proof of a fully missing order."}, sources=('refund-policy-v1', 'packing-slip', 'customer-report'))
    capability = toolkit.skill(name='refunds', tools=(normalize, price, policy))
    normalizer = tool_agent('normalize', normalize, skills=(capability,))
    classifier = toolkit.Agent('classify', runtime=reasoner or toolkit.runtime(provider='python-runtime'), framework=toolkit.framework(framework), skills=() if reasoner else (toolkit.skill(name='classification', tools=(classify,)),), instructions='Interpret the customer note against packing slip and received items. Apply reference policy. Return only JSON: order_id, amount, total_units, missing_units, short evidence-based reason, sources including packing-slip and customer-report. Copy original amount unchanged; Python calculates refunds.' if reasoner else '', contract={'output_schema': SCHEMA})

    def review(data):
        if not interactive:
            return {'status': 'pending_review'}
        approved = toolkit.pause({'question': 'Approve partial refund?', 'refund': data.refund, 'order_id': data.order_id})
        if type(approved) is not bool:
            raise TypeError('Approval must be bool')
        return {'status': 'approved' if approved else 'rejected'}
    graph = toolkit.Graph(RefundState, output_schema=RefundOutput)
    graph.add_node('normalize', normalizer)
    graph.add_node('classify', classifier)
    graph.add_node('price', tool_agent('price', price))
    graph.add_node('policy', tool_agent('policy', policy))
    def decision_step(state):
        return {'needs_review': state.refund > state.review_threshold}
    graph.add_node('decision', decision_step)
    graph.add_node('review', review)
    def approve_step(state):
        return {'status': 'approved'}
    graph.add_node('approve', approve_step)
    graph.add_edge(toolkit.START, 'normalize')
    graph.add_edge('normalize', 'classify')
    graph.add_edge('classify', 'price')
    graph.add_edge('classify', 'policy')
    graph.add_edge(['price', 'policy'], 'decision')
    graph.add_conditional_edges('decision', lambda state: 'review' if state.needs_review else 'approve', ['review', 'approve'])
    graph.add_edge('review', toolkit.END)
    graph.add_edge('approve', toolkit.END)
    return toolkit.System('refunds', graph=graph, context=domain, memory=toolkit.Memory())

def check_result(output):
    return output.ok and output.data['order_id'] == 'R-17' and (output.data['refund'] == 120) and (output.data['currency'] == 'MXN') and (output.data['missing_units'] == 1) and ({'packing-slip', 'customer-report'} <= set(output.data['sources'])) and output.check_invariants().ok

def demonstrate(framework='native'):
    definition = build_system(framework, interactive=True)
    program = definition.compile()
    waiting = program.run(CASE, timeout_s=40)
    assert waiting.status == 'paused', waiting.to_dict()
    final = program.resume(waiting, True)
    assert check_result(final), final.to_dict()
    graph = toolkit.Graph(RefundState, output_schema=RefundOutput)
    graph.add_node('refund', build_system(framework))
    graph.add_edge(toolkit.START, 'refund')
    graph.add_edge('refund', toolkit.END)
    episode = toolkit.Environment('daily-refunds', graph=graph, records=(CASE, CASE), state={'total': 0}, update=lambda state, row, result: {'total': state['total'] + result.data['refund']}).run(timeout_s=40)
    evaluation = toolkit.Eval('refund-contract', build_system(framework), ({'input': CASE, 'expected': {'ok': True}},), checks=(lambda result, case: {'ok': check_result(result)},)).run(timeout_s=40)
    assert episode.ok and episode.data['summary']['state'] == {'total': 240}, episode.to_dict()
    assert evaluation.ok, evaluation.to_dict()
    restored = toolkit.RunResult(**final.to_dict())
    assert restored.check_invariants().ok
    return {'orchestration': 'langgraph', 'framework': framework, 'provider': 'python-runtime', 'input': CASE, 'process': ['normalize', 'classify', 'price + policy', 'decision', 'pause/resume'], 'output': final.data, 'run_results': [waiting.to_dict(), final.to_dict(), episode.to_dict(), evaluation.to_dict()], 'human_lineage': final.lineage(name='Refund R-17').render(), 'agent_lineage': final.lineage().to_prompt_context(), 'memory': definition.memory.read()}
