# Evaluar sin repetir · 2.1.4.dev7

Restaurar RunResult y evaluar evidencia guardada.

```python
from examples.patterns.saved_execution_eval.example import run
report = run()
```

Input → proceso → output: Suma 2 + 3 → serialización → Eval acepta total 5 sin volver a ejecutar el cálculo.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--saved_execution_eval--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
