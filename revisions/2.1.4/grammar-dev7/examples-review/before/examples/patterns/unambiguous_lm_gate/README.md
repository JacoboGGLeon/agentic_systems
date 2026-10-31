# Exigir una respuesta literal · 2.1.4.dev7

Distinguir coincidencia exacta de parecido textual.

```python
from examples.patterns.unambiguous_lm_gate.example import run
report = run()
```

Input → proceso → output: VALID, VALID., invalid y vacío → Eval → solo VALID aceptado; respuestas guardadas, sin modelo.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--unambiguous_lm_gate--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
