# Tutorials

Abre un notebook, importa la librería y ejecuta sus celdas. Cada capítulo
introduce una necesidad y muestra **input → proceso → output**.

Empieza por 00–03. Añade Environment y Eval en 04–05. Los capítulos siguientes
son para integrar proveedores, consultar trazas o preparar una aplicación mayor.

| Capítulo | Pregunta que resuelve |
|---|---|
| [00](00_api.ipynb) | ¿Cómo construyo algo y obtengo su resultado? |
| [01](01_tools_skills.ipynb) | ¿Cómo reutilizo operaciones con Tools y Skills? |
| [02](02_agent_flows.ipynb) | ¿Cómo ordena su trabajo un Agent? |
| [03](03_system_flows.ipynb) | ¿Cómo coordina varios Agents un System? |
| [04](04_environment.ipynb) | ¿Cómo proceso registros y mantengo memoria? |
| [05](05_eval.ipynb) | ¿Cómo compruebo que el resultado es correcto? |
| [06](06_runtime_framework.ipynb) | ¿Cómo elijo proveedor y framework? |
| [07](07_results_limits.ipynb) | ¿Cómo reutilizo, observo y limito una ejecución? |
| [08](08_model_serving.ipynb) | ¿Cómo declaro un modelo y su servidor? |
| [09](09_order_challenge.ipynb) | ¿Cómo se conectan todas las piezas en pedidos? |
| [10](10_contracts_judges.ipynb) | ¿Cómo añado contratos, salida estructurada y un juez? |

Todos usan la API 2.1.3 instalada. Python Runtime ejecuta operaciones exactas;
las celdas no llaman proveedores externos. La lección de serving prepara
configuración y no inicia GPU. El juez fixture comprueba un protocolo, no la
capacidad semántica de un modelo.

`lesson_examples.py` localiza las aplicaciones compartidas con independencia
del directorio de trabajo. Las celdas de aprendizaje no contienen rutas,
guardas ni banderas de validación. El validador las añade a una copia ejecutada;
su funcionamiento está en la [guía de desarrollo](../docs/VALIDATION_213.md).

[Examples](../examples/README.md) · [Referencia completa](../docs/API_213_SURFACE.md) ·
[Evidencia actual](../revisions/2.1.3/framework-evidence/REPORT.md)
