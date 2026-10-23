# Resolver un reembolso

Aplicar una política de negocio pequeña y visible.

```python
from examples.applications.refund_resolution.example import run

result = run()
result
```

280 MXN, cuenta de 90 días → regla declarada → approved; datos sintéticos.

Código:
- [Current implementation](../../../examples/applications/refund_resolution/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/refund_resolution/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/refund_resolution/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: designed. Not implemented, not executed and not certified. Native is the intended framework; Python is deterministic control and OpenAI/Bedrock API key/Ollama are intended LLM routes. The earlier eight-constructor matrix and proposed extra budget were not executed or authorized.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Design and execution boundary](../../../examples/applications/refund_resolution/DESIGN.md)

</details>
