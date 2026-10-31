# Bloquear un falso positivo · 2.1.4.dev7

Impedir que un juez fixture apruebe una respuesta incorrecta.

```python
from examples.patterns.fixed_judge_pilot.example import run
report = run()
```

Input → proceso → output: WRONG → expectativa VALID y juez optimista → caso rechazado, conservando ambos resultados.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--patterns--fixed_judge_pilot--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
