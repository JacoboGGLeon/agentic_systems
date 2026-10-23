# Conservar un fallo

Inspeccionar errores, eventos y linaje de una operación fallida.

```python
from examples.patterns.controlled_failure.example import run

result = run()
result
```

Producto A17 → Tool lanza LookupError → RunResult fallido con evidencia e invariantes válidas.

Código:
- [Current implementation](../../../examples/patterns/controlled_failure/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/controlled_failure/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/controlled_failure/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: accepted-2.1.2. Published acceptance includes one controlled failure/serialization check per route/pass (32 in total). Failure is the expected behavior; it remains visible in RunResult.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Published exact-wheel acceptance summary](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.2/final-certification-summary.json)
- [Published release](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.2)

</details>
