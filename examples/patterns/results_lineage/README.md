# Results Lineage — API 2.1.3

JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage.

```python
from examples.results_lineage.example import run

result = run()
result
```

Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

Código:
- [Runnable example](../../../examples/results_lineage/example.py)
- [Walkthrough](../../../examples/results_lineage/README.md)

Validación: **Offline ejecutado**. JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage. Final artifact binding is recorded in implementation evidence. No real inference.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/results_lineage/run.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/results_lineage/runresults.json)
