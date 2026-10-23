# Asignar responsables a evidencia

Mostrar un reemplazo público y sintético del experimento retirado.

```python
from examples.applications.retired_accountability_otc.example import run

result = run()
result
```

Dos afirmaciones → comprobar owner/evidence → C2 sin responsable ni respaldo. El código privado original no se recuperó.

Código:
- [Current implementation](../../../examples/applications/retired_accountability_otc/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/retired_accountability_otc/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/retired_accountability_otc/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: retired. The previous catalog explicitly excluded this retired reference. It is now listed for completeness; no validation or migration is claimed.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Retirement scope](../../../examples/history/retired.md)

</details>
