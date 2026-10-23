# Model Serving — API 2.1.3

Artifact and explicit server configuration/inspection only. Lifecycle exercised separately with fake HTTP/process in SDK tests; no GPU or model started.

```python
from examples.model_serving.example import run

result = run()
result
```

Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

Código:
- [Runnable example](../../../examples/model_serving/example.py)
- [Walkthrough](../../../examples/model_serving/README.md)

Validación: **Offline ejecutado**. Artifact and explicit server configuration/inspection only. Lifecycle exercised separately with fake HTTP/process in SDK tests; no GPU or model started. Final artifact binding is recorded in implementation evidence. No real inference.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/model_serving/run.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/model_serving/runresults.json)
