# Ejecutar tres actores · 2.1.4.dev7

Usar los tres SDKs con Python determinista.

```python
from examples.validation.provider_framework_conformance.example import run
report = run()
```

Input → proceso → output: value=3 → Tool echo en native, OpenAI Agents y Strands, orquestados por LangGraph → misma evidencia; la matriz live se documenta aparte.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--validation--provider_framework_conformance--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
