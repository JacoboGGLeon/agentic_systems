# Calcular una factura · 2.1.4.dev7

Separar cálculo verificable de presentación.

```python
from examples.patterns.semantic_calculation.example import run
report = run()
```

Input → proceso → output: Tres unidades de 100 → subtotal e impuesto del 16% → total 348.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--semantic_calculation--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
