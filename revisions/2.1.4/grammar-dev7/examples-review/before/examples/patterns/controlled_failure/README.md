# Conservar un fallo · 2.1.4.dev7

Inspeccionar errores, eventos y linaje de una operación fallida.

```python
from examples.patterns.controlled_failure.example import run
report = run()
```

Input → proceso → output: Producto A17 → Tool lanza LookupError → RunResult fallido con evidencia e invariantes válidas.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--controlled_failure--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
