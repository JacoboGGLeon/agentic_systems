# Recorrer un episodio

Acumular memoria sin contaminar la siguiente ejecución.

```python
from examples.patterns.long_environment.example import run

result = run()
result
```

Treinta movimientos de +1 → Environment con memoria → balance 30 en dos episodios independientes.

Código:
- [Current implementation](../../../examples/patterns/long_environment/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/long_environment/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/long_environment/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: offline-only. The control is deterministic. A separately reported hybrid saved candidate used eight Python Agents plus one LLM Agent on one route; it does not establish an all-LLM or complete long-case matrix.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Long-case topology and evaluation limits](../../../docs/long-evals-v1.md)

</details>
