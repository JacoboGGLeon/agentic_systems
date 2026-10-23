# Validar una afirmación tipada

Rechazar datos que incumplen el esquema de entrada.

```python
from examples.patterns.typed_claim_review.example import run

result = run()
result
```

Una entrada válida y otra con texto numérico → Tool con esquema estricto → éxito y fallo conservados.

Código:
- [Current implementation](../../../examples/patterns/typed_claim_review/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Ejecución actual](../../../examples/patterns/typed_claim_review/evidence/current.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Live source pilots: v1 OpenAI/langgraph 3/6 and Ollama/native 0/6; v2 OpenAI/langgraph 1/3 and Ollama/native 0/3. Extraction/audit defects remain unresolved. Offline callback tests across frameworks do not supply live framework acceptance.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Results and limits](../../../docs/typed-claim-review-results.md)

</details>
