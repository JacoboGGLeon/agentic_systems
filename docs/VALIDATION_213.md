> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Validación de desarrollo 2.1.3

Para aprender a usar el SDK, abre [tutorials](../tutorials/README.md) o
[examples](../examples/README.md). Esta página describe sus arneses de validación.
Los notebooks enseñan declaraciones y ejecución; las rutas de evidencia,
guardas y contadores viven en los validadores.

## Offline

Instala el wheel publicado sin modo editable y las dependencias de desarrollo.
Selecciona un directorio nuevo mediante `AGENTIC_213_EVIDENCE_DIR` para una campaña:

```bash
python scripts/test_offline_213.py
python scripts/execute_notebooks_213.py
python examples/run_offline_213.py
python scripts/validate_examples_213.py
python examples/agentic_systems_studio/test_offline.py
python examples/catalog_tools.py --check
```

El ejecutor de notebooks usa kernels nuevos, el SDK instalado y el directorio
propio de cada notebook. Añade a una copia dos celdas de guarda/captura; no aporta
nombres de las aplicaciones. Core es autónomo y ya no importa lesson_examples.
Las celdas con tags `live`, `local-network` o `ui` se omiten **solo en este perfil**
y constan como omitidas. Pasar el perfil offline no acredita esas secciones.

Los 15 examples canónicos y las 34 adaptaciones conservan RunResult y lineage.
Las adaptaciones se aíslan en procesos nuevos. MCP/A2A usa servicios locales
reales con un límite de cero llamadas de inferencia; las otras adaptaciones
bloquean conexiones de aplicación. IAM/GPU solo valida configuración offline.

`execute_local_lessons_213.py` ejecuta todas las celdas originales de los dos
notebooks con servicios/UI. Comprueba MCP y A2A, apertura de Studio, health y
cierre del servidor. El contador de transporte autoriza **cero** inferencias;
solo registra los puertos efímeros de los servicios locales de la prueba.

## Live

Una campaña exige autorización propia y un ledger nuevo; nunca se reinicia uno
existente. Esta campaña se creó con `start_learning_campaign_213.py` a partir
de la autorización explícita de USD 10 y 300 llamadas. No ejecutes de nuevo ese
script para reutilizar un presupuesto ni para automatizar autorizaciones futuras.

`execute_live_notebooks_213.py` ejecuta las celdas originales de los tres
notebooks de proveedor en los cuatro frameworks. La copia parametriza solo
el framework, conserva los hashes de fuente y registra cada intento.
`examples/framework_interop/run_campaign.py` comprueba handoffs/guardrails,
MCP/A2A, checkpoint, pedidos, conversación y widgets reales de Studio.

Todos comparten el mismo ledger mediante bloqueo entre procesos. Antes de cada
transporte se comprueban endpoint, modelo, límite de salida y reserva disponible.
Los hooks permanecen activos hasta terminar el proceso y sus trabajadores,
incluidas respuestas después de un timeout. Las reservas son cotas conservadoras,
no facturación; se incluyen Ollama, fallos y reintentos. No hay sustitución de rutas.

## Evidencia y mantenimiento

[Resultados actuales](LEARNING_VALIDATION_213.md) · [RunResult/lineage](RUNRESULTS_LINEAGE_213.md) ·
[Inventario de notebooks](NOTEBOOK_INVENTORY_213.md).

`write_tutorials_213.py` y `organize_learning_213.py` generan las 19 lecciones.
`inventory_notebooks_213.py` registra conceptos directos, referencias compartidas,
métodos, parámetros y hashes. `report_learning_213.py` cruza capturas y fuentes;
una importación o una cadena de provider no cuenta como ejecución live.

La evidencia original del release se conserva sin reescribirla. El archivo
`revisions/2.1.3/published-learning-source.zip` guarda las fuentes didácticas y
documentación originales; su hash y cada miembro se verifican contra el manifiesto
original. `prepare_release_213.py` comprueba los bytes publicados del SDK y Studio
y ese snapshot; las lecciones actuales se verifican por separado. Así un cambio
de README no se atribuye a una nueva aceptación del wheel ni exige republicarlo.
