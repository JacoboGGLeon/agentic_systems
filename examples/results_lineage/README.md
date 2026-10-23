# Results Lineage — API 2.1.3

JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage.

```python
from examples.results_lineage.example import run

report = run()
report
```

Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

La declaración completa está en [example.py](example.py). El resultado conserva
la entrada, el proceso y la salida observados, con aserciones del contrato.

Validación offline: JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage. Final artifact binding is recorded in implementation evidence. No real inference.
[Evidencia actual](evidence/run.json). [Resultados y límites de la campaña](../../revisions/2.1.3/framework-evidence/REPORT.md).
El mantenimiento y los runners están en [la guía de validación](../../docs/VALIDATION_213.md).
