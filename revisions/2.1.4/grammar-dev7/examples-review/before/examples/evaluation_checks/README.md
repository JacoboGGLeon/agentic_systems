# Evaluation Checks — API 2.1.4.dev7

Exact expected, custom checks, reward metrics, explicit fixture judge and negative control. No semantic model validation.

```python
from examples.evaluation_checks.example import run
report = run()
```

Input → proceso → output: Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

[Declaración](example.py) · [Evidencia](../../revisions/2.1.4/pydantic-dev4/examples/examples--evaluation_checks--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
