# Environment y rewards · 2.1.4.dev8

La API pública ofrece graph, records, state, observe, update, stop y max_steps.
No tiene reward=, espacios/action_space, reset/step públicos ni aprendizaje de
políticas. El mecanismo reward_fn de la implementación histórica interna no
constituye otra API pública soportada.

Se puede calcular una recompensa con la gramática actual, en update, y guardarla
en state/history. El ejemplo integrado compara la decisión con un oráculo de
referencia del Environment: 1 si coincide, 0 si no. Ese oráculo no se entrega
como input al System; observe solo proyecta amount.

```python
def observe_payment(record, state):
    return {"amount": record["amount"]}

def update_day(state, record, result):
    reward = 1 if result.ok and result.data["status"] == record["expected_status"] else 0
    return {"processed": state["processed"] + 1,
            "reward": reward,
            "total_reward": state["total_reward"] + reward}
```

Esto demuestra feedback episódico como dato de negocio. No activa entrenamiento,
optimización de políticas ni una API RL completa. Formalizar reward requeriría
un contrato explícito para episodios, fallos, tipos, acumulación y evidencia;
no se añade un constructor o comportamiento de aprendizaje implícito.

[Fuente completa](../examples/checked_composition/example.py) ·
[Notebook](../examples/checked_composition/01_checked_composition.ipynb).
