# Revisar referencias y causalidad

Aplicar comprobaciones explícitas sobre afirmaciones estructuradas.

```python
from examples.patterns.claim_review.example import run

result = run()
result
```

Fuente ausente y causalidad sin evidencia declarada → dos hallazgos → accepted=False.

Código:
- [Current implementation](../../../examples/patterns/claim_review/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/claim_review/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/claim_review/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Held-out verdict matches were Bedrock/native 6/6, OpenAI/langgraph 5/6 and Ollama/native 5/6, with additional citation limits. Exposed v3/v4/v5 regressions are separate experiments; v5 accepted 4/6, not a complete matrix. Correct binary results do not certify citation quality.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Pilot](../../../docs/claim-evaluator-pilot.md)
- [Held-out and long-case sample](../../../docs/claim-acceptance-v1-results.md)
- [Regression v3](../../../docs/claim-regression-v3-results.md)
- [Regression v4](../../../docs/claim-regression-v4-results.md)
- [Regression v5](../../../docs/claim-regression-v5-results.md)

</details>
