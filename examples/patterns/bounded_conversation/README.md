# Acotar una conversación

Mantener una ventana de contexto explícita.

```python
from examples.patterns.bounded_conversation.example import run

result = run()
result
```

Cuatro mensajes → últimas tres entradas, longitud acotada → historia conservada.

Código:
- [Current implementation](../../../examples/patterns/bounded_conversation/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/bounded_conversation/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/bounded_conversation/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Historical conversation runs include passes and failures. A local artifact named studio-long-certified.json recorded failures for all three LLM providers; its filename is not acceptance. Source reports also retain judge schema and explanation defects. No blanket 2.1.2 conversation certification is claimed.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Studio implementation and contract](../../../examples/agentic_systems_studio/README.md)
- [Preserved calibration and notebook limits](../../../docs/two-phase-212-status.md)

</details>
