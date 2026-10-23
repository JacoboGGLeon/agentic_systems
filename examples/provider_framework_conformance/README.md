# Ejecutar cuatro frameworks

Usar los cuatro SDKs con Python determinista.

```python
from examples.provider_framework_conformance.example import run

report = run()
report
```

value=3 → Tool echo en native, LangGraph, OpenAI Agents y Strands → misma evidencia; la matriz live se documenta aparte.

La declaración completa está en [example.py](example.py). El resultado conserva
la entrada, el proceso y la salida observados, con aserciones del contrato.

Validación offline: Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.
[Evidencia actual](evidence/run.json). [Resultados y límites de la campaña](../../revisions/2.1.3/framework-evidence/REPORT.md).
El mantenimiento y los runners están en [la guía de validación](../../docs/VALIDATION_213.md).
