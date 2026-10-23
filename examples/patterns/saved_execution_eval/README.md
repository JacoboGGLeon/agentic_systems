# Evaluar sin repetir

Restaurar RunResult y evaluar evidencia guardada.

```python
from examples.patterns.saved_execution_eval.example import run

result = run()
result
```

Suma 2 + 3 → serialización → Eval acepta total 5 sin volver a ejecutar el cálculo.

Código:
- [Current implementation](../../../examples/patterns/saved_execution_eval/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Ejecución actual](../../../examples/patterns/saved_execution_eval/evidence/current.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. One OpenAI/openai-agents episode: 7/7 original verdicts accepted and 7/7 negatives rejected; one explanation invented an increment. Later claim-based review retained irrelevant citations for six nonfactual fragments. Neither result certifies every explanation or the full matrix.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Original semantic pilot](../../../docs/long-evals-v1.md)
- [Later claim-based evaluation](../../../docs/claim-acceptance-v1-results.md)

</details>
