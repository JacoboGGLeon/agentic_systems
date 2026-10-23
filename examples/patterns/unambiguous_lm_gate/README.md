# Exigir una respuesta literal

Distinguir coincidencia exacta de parecido textual.

```python
from examples.patterns.unambiguous_lm_gate.example import run

result = run()
result
```

VALID, VALID., invalid y vacío → Eval → solo VALID aceptado; respuestas guardadas, sin modelo.

Código:
- [Current implementation](../../../examples/patterns/unambiguous_lm_gate/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Ejecución actual](../../../examples/patterns/unambiguous_lm_gate/evidence/current.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Historical source pilots: OpenAI/native and Ollama/native passed 10/10; Bedrock Nova/langgraph omitted two unknown decisions and failed 8/10. A separately recorded Qwen/langgraph A/B passed 10/10 without erasing Nova. This is not full matrix or exact-wheel acceptance.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Contract and observed pilot routes](../../../docs/unambiguous-lm-gate.md)

</details>
