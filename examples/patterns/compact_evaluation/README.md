# Evaluar y resumir evidencia

Evaluar una ejecución guardada y consultar su traza.

```python
from examples.patterns.compact_evaluation.example import run

result = run()
result
```

Suma 2 + 3 → guardar RunResult → Eval, trace y lineage sin repetir el candidato.

Código:
- [Current implementation](../../../examples/patterns/compact_evaluation/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/compact_evaluation/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/compact_evaluation/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Source matrix: 20/32 case gates passed; 8/16 routes passed both cases, including four deterministic Python controls. Ollama failed both cases on all four frameworks; OpenAI and Bedrock also retain failed cases. Not release certification.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Matrix and failure classification](../../../docs/compact-matrix-results.md)

</details>
