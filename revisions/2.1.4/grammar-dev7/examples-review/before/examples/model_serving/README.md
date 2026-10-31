# Model Serving — API 2.1.4.dev7

Artifact and explicit server configuration/inspection only. Lifecycle exercised separately with fake HTTP/process in SDK tests; no GPU or model started.

```python
from examples.model_serving.example import run
report = run()
```

Input → proceso → output: Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

[Declaración](example.py) · [Evidencia](../../revisions/2.1.4/pydantic-dev4/examples/examples--model_serving--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
