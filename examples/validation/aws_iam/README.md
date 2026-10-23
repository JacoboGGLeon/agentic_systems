# Preparar AWS IAM

Declarar Bedrock sin una API key embebida.

```python
from examples.validation.aws_iam.example import run

result = run()
result
```

Modelo y región → runtime → configuración; el proceso de destino debe usar su rol IAM sin bearer token. Autenticación pendiente.

Código:
- [Current implementation](../../../examples/validation/aws_iam/example.py)

Validación: **Configuración; entorno pendiente**. Configuración construida e inspeccionada. El entorno de destino no se ejecutó.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/validation/aws_iam/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/validation/aws_iam/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: pending-2.1.2. Earlier-release evidence is recorded in the changelog. vLLM/Colab, AWS IAM and ADA IAM remain explicitly pending for the exact published 2.1.2 wheel. ADA is an enterprise environment, not a provider or an installed [ada] extra.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Published 2.1.2 pending routes](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.2/final-certification-summary.json)
- [Historical release scope](../../../CHANGELOG.md)
- [Post-release validation instructions](../../../docs/POST_RELEASE_VALIDATION.md)

</details>
