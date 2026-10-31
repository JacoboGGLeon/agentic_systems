# Perfilar datos · 2.1.4.dev7

Detectar duplicados y valores ausentes.

```python
from examples.applications.data_quality.example import run
report = run()
```

Input → proceso → output: Dos registros → conteos deterministas → un ID duplicado y un importe ausente.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--applications--data_quality--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
