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

- [Measured offline report](../../../revisions/2.1.3/closeout-evidence/REPORT.md)
- [Exact artifact and evidence hashes](../../../revisions/2.1.3/implementation-evidence/manifest.json)
