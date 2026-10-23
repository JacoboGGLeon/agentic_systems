# Evaluation Checks — API 2.1.3

Exact expected, custom checks, reward metrics, explicit fixture judge and negative control. No semantic model validation.

```python
from examples.evaluation_checks.example import run

result = run()
result
```

Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

Código:
- [Runnable example](../../../examples/evaluation_checks/example.py)
- [Walkthrough](../../../examples/evaluation_checks/README.md)

Validación: **Offline ejecutado**. Exact expected, custom checks, reward metrics, explicit fixture judge and negative control. No semantic model validation. Final artifact binding is recorded in implementation evidence. No real inference.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/evaluation_checks/run.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/evaluation_checks/runresults.json)
