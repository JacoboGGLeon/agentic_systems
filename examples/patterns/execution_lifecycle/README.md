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

- [Measured offline report](../../../revisions/2.1.3/closeout-evidence/REPORT.md)
- [Exact artifact and evidence hashes](../../../revisions/2.1.3/implementation-evidence/manifest.json)
