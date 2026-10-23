# Execution Lifecycle — API 2.1.3

Direct/compiled and async execution, shared action limits and controlled exhaustion.

```python
from examples.execution_lifecycle.example import run

result = run()
result
```

Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

Código:
- [Runnable example](../../../examples/execution_lifecycle/example.py)
- [Walkthrough](../../../examples/execution_lifecycle/README.md)

Validación: **Offline ejecutado**. Direct/compiled and async execution, shared action limits and controlled exhaustion. Final artifact binding is recorded in implementation evidence. No real inference.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/execution_lifecycle/run.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/execution_lifecycle/runresults.json)
