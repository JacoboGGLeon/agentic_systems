# Bloquear un falso positivo

Impedir que un juez fixture apruebe una respuesta incorrecta.

```python
from examples.patterns.fixed_judge_pilot.example import run

result = run()
result
```

WRONG → expectativa VALID y juez optimista → caso rechazado, conservando ambos resultados.

Código:
- [Current implementation](../../../examples/patterns/fixed_judge_pilot/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/fixed_judge_pilot/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/fixed_judge_pilot/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Six native pilot cases, 14 guarded requests. OpenAI schema failures, Bedrock unsupported positive explanation and budget-interrupted negative, Ollama citation/type errors and false semantic approval. Expansion was blocked; no release certification.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Fixed v6 pilot report](../../../docs/judge-v6-pilot-results.md)

</details>
