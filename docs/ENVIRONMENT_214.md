# Environment and rewards · 2.1.4

The public API exposes graph, records, state, observe, update, stop and max_steps. It has no reward= parameter, spaces/action_space, public reset/step methods or policy learning. Historical internal reward_fn implementation is not a second supported public API.

Compute an explicit reward in update and retain it in state/history. The integrated example compares a decision against an Environment reference oracle: 1 for a match, 0 otherwise. observe projects only amount; the oracle is not supplied to the System.

```python
def observe_payment(record, state):
    return {"amount": record["amount"]}

def update_day(state, record, result):
    reward = 1 if result.ok and result.data["status"] == record["expected_status"] else 0
    return {"processed": state["processed"] + 1,
            "reward": reward,
            "total_reward": state["total_reward"] + reward}
```

This demonstrates episodic feedback as business data, not training, policy optimization or a complete RL API. A formal reward feature would require explicit contracts for episodes, failures, types, accumulation and evidence; no constructor or learning behavior is implicitly added.

[Complete source](../examples/checked_composition/example.py) · [English notebook view](../examples/checked_composition/01_checked_composition.md).
