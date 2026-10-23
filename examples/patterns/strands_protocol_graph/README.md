# Conectar MCP y A2A

Usar servicios locales reales desde Strands.

```python
from examples.patterns.strands_protocol_graph.example import run

result = run()
result
```

Valor conocido → MCP Streamable HTTP y agente A2A → evidencia remota; modelos deterministas y cero inferencia.

Código:
- [Current implementation](../../../examples/patterns/strands_protocol_graph/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/strands_protocol_graph/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/strands_protocol_graph/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: historical-pass. Three historical routes passed on a 2.1.0 wheel with SHA-256 46fa5e7e117d6482a4d15332d52d9520b897fd2beeef92bdcb816bf93896b9d5. This differs from the published 2.1.2 wheel. Shipping the source bundle does not transfer that acceptance.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Historical summary extract](../../../examples/evidence/historical-protocol-summary.json)
- [Challenge contract](../../../semantic_challenges/strands_protocol_graph/README.md)

</details>
