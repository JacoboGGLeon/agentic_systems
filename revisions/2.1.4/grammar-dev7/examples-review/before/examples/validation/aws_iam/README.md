# Preparar AWS IAM · 2.1.4.dev7

Declarar Bedrock sin una API key embebida.

```python
from examples.validation.aws_iam.example import run
report = run()
```

Input → proceso → output: Modelo y región → runtime → configuración; el proceso de destino debe usar su rol IAM sin bearer token. Autenticación pendiente.

[Declaración](example.py) · [Evidencia](../../../revisions/2.1.4/pydantic-dev4/examples/examples--validation--aws_iam--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
