# Recorrer un episodio · 2.1.4.dev7

Acumular memoria sin contaminar la siguiente ejecución.

```python
from examples.patterns.long_environment.example import run
report = run()
```

Input → proceso → output: Treinta movimientos de +1 → Environment con memoria → balance 30 en dos episodios independientes.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--long_environment--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
