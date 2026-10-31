# Conservar un fallo · 2.1.4

Inspeccionar errores, eventos y linaje de una operación fallida.

La composición y las aserciones están visibles en [el código](example.py).
Lee las declaraciones de Tools, Agents y Graph antes de ejecutar el ejemplo.

Input → proceso → output: Producto A17 → Tool lanza LookupError → RunResult fallido con evidencia e invariantes válidas.

[Declaración](example.py) · [Evidencia dev8](../../../revisions/2.1.4/grammar-dev8/closure/examples/examples--patterns--controlled_failure--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../../revisions/2.1.4/contracts-dev5/REPORT.md). Las revisiones previas se conservan como evidencia histórica.
