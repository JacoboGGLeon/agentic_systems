# Respetar el alcance · 2.1.4.dev7

Rechazar una operación no declarada.

```python
from examples.patterns.scope_clarification.example import run
report = run()
```

Input → proceso → output: transfer_money → consulta de capacidades → accepted=False y operaciones disponibles.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--scope_clarification--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
