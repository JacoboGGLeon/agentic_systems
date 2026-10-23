# Validación de desarrollo 2.1.3

Esta página es para mantener la librería. Para aprender a usarla, empieza en
[tutorials](../tutorials/README.md) o [examples](../examples/README.md).

Los validadores contienen el manejo de rutas, instalación, guardas offline y
presupuesto. Los ejemplos públicos exponen `run()` y las declaraciones del SDK.

```text
python scripts/test_offline_213.py
python scripts/execute_tutorials_213.py
python scripts/validate_examples_213.py
python examples/agentic_systems_studio/test_offline.py
python examples/catalog_tools.py --check
```

`execute_tutorials_213.py` ejecuta copias de los notebooks en kernels nuevos e
inyecta dos celdas exclusivas de validación. Las fuentes del curso no contienen
esas celdas. Las guardas bloquean inferencia y procesos de la aplicación;
Jupyter y asyncio usan su transporte local. No se introducen nombres públicos
de apoyo que oculten imports faltantes en las lecciones.

`validate_examples_213.py` ejecuta las 34 adaptaciones en procesos separados.
MCP/A2A usa transportes locales reales con una asignación de cero inferencias;
las otras adaptaciones bloquean red. Las rutas IAM/GPU solo preparan y validan
configuración, y no acreditan ejecución en su entorno.

La campaña live se orquesta mediante `examples/framework_interop/run_campaign.py`.
Es una herramienta técnica, con fases y selección de casos, no la interfaz del
example. Mantiene un registro persistente y bloqueo entre procesos; verifica
modelo, endpoint y tope antes de cada transporte. Conserva fallos y reintentos.
No se debe abrir una campaña nueva reutilizando una autorización anterior.

La [evidencia actual](../revisions/2.1.3/framework-evidence/REPORT.md) identifica
el wheel, las fuentes de aplicaciones, las dependencias, los intentos y el
consumo reservado. Las reservas son cotas conservadoras, no facturación.
Esta tarea no publica ni modifica artefactos previamente publicados.
