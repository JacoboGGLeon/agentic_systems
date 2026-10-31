# Gramática única y comprobación · 2.1.4.dev6

Revisión local sin publicar. Un Agent organiza una capacidad; un System coordina la aplicación. Ambos pueden tener grafos originales LangGraph; Environment añade su grafo episódico. check valida construcción, no semántica del negocio.

Wheel SHA-256: `ab41fbb251a04ace7d93b9650754632720d4c12715787b0ac5dbf7eec90f3df9`. [Wheel](builds/01/agentic_systems-2.1.4.dev6-py3-none-any.whl) · [sdist](builds/01/agentic_systems-2.1.4.dev6.tar.gz) · [Instalación](installation.json) · [Snapshot de fuente/commit](source-snapshot.json). El commit identifica la base; los cambios locales quedan identificados por hashes, no por atribuirlos al commit antiguo.

Aceptación offline con Python **3.14.2**: **353 pruebas**, **28/28 notebooks (22 tutorials + 6 examples)**, **56/56 entrypoints**, más **1 example MCP/A2A local** con SDK fixture y cero inferencia. **16/16 palabras core** ejercitadas; cinco reexportaciones LangGraph se informan aparte. [JUnit](offline-junit.xml) · [Examples](examples-offline.json) · [Protocolos](local-protocols.json) · [Resumen](summary.json).

## Contratos y evidencia

| Contrato | Comprobación |
| --- | --- |
| 1. Sin Limits/limits=/max_actions | Exports y firmas negativas; runtime rechaza opciones retiradas |
| 2. Anidamiento independiente del conteo | 12 envoltorios y grafo de 260 nodos; mismo resultado sin cuota |
| 3. Plazo y controles | Plazo compartido, scheduler/reintentos, intentos observados y consumo; timeout cooperativo |
| 4. Context directo | Tools/nodos sync/async, Memory seleccionada y aislamiento de linaje entre ramas |
| 5. Contratos estrictos | Proyección explícita, ausencias y null requerido; no defaults de reparación |
| 6. Continuaciones y Eval | Trabajo completado conservado; pausa/reanudación; Eval rechaza pausa |
| 7. Material y scaffolder | 28 notebooks, 56 entrypoints, MCP/A2A local; proyecto generado con tres actores Python; skill validada |
| 8. Artefacto independiente | Wheel/sdist nuevos, instalación externa, 119 hashes RECORD y suite offline del wheel |

## Cambios y hallazgos

Se retiran Limits, Action y Runtime públicos. runtime mantiene proveedor y scheduler; run(timeout_s=...) fija el plazo raíz. nodes_observed es telemetría. Tools y nodos leen *, context: toolkit.Context. check acepta los seis componentes y fábricas sync/async, devolviendo el componente original sin ejecutar el trabajo.

Los nodos que llaman a child.run y devuelven una proyección conservan todos los resultados hijos. Una composición que ya incluye un hijo no lo duplica en el árbol. Las regresiones comprueban eventos, identidad, fallos descartados por el nodo y proyecciones de negocio. Los reintentos conservan intentos previos completos y suman consumo; no duplican toda la traza en el camino normal sin reintentos. Un timeout informa intentos reales y puede dejar un trabajador pendiente; un RunResult es una fotografía, por lo que el contador externo debe seguir activo hasta su terminación.

La migración corrigió proyecciones Pydantic y captura de variables de nodos creados en un bucle. El ejemplo de ciclo de vida pasó de la cuota retirada a un timeout controlado. El ejemplo de instalación actualiza los exports esperados; su fallo original y repetición quedan conservados. Los intentos fuente fallidos y el guard de procesos corregido para el formato Windows están en attempts/ y source-validation/. No se relajan oráculos ni contratos para obtener PASS.

El proyecto generado por CLI y skill ejecutó native/OpenAI Agents/Strands con Python y su notebook en kernel nuevo. [Evidencia](scaffolder.json). Studio pasó controlador, memoria y UI dentro de las 353 regresiones; esto no acredita todas las interacciones de UI ni LM reales. [MCP/A2A](local-protocols.json) usa transportes de loopback reales y modelos fixture, con conexiones externas prohibidas; ambos servicios se cierran al terminar.

## Alcance y pendientes

**Cero inferencia nueva y cero publicación.** La campaña dev5 conserva exactamente su hash: 148/150 solicitudes, USD 0.875040 reservados de USD 5. El wheel dev5 build03 conserva su hash. La aceptación live anterior no se atribuye a dev6.

Los tests prueban contratos de los proveedores y SDK con fixtures. OpenAI, Bedrock, Ollama cloud/GPU y vLLM no se vuelven a consultar. Bedrock/null, interoperabilidad Ollama cloud, Studio/Bedrock e IAM/ADA mantienen su trabajo live pendiente; vLLM continúa aplazado. CI Python 3.10–3.14 no se ejecutó en esta tarea. Memory y continuación siguen siendo locales al proceso; no se promete persistencia durable, preempción ni rollback.

[Ejemplo explícito](../../../examples/checked_composition/01_checked_composition.ipynb) · [API](../../../docs/API_214.md) · [Firmas](../../../docs/API_214_SURFACE.md) · [Inventario](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults/Memory/linaje](../../../docs/RUNRESULTS_LINEAGE_214.md).

## Entregables locales

[Studio wheel](bundles/agentic_systems_studio-2.1.4.dev6-py3-none-any.whl),
[skill](bundles/agentic-systems-skill-2.1.4.dev6.zip) y
[tutorials/examples/documentación](bundles/agentic-systems-learning-2.1.4.dev6-r2.zip)
son entregables separados del SDK. [Hashes](bundles/hashes.json).
El primer bundle didáctico se conserva como intento previo; r2 corrige una
nota histórica, sin cambiar código ejecutado ni bytes del SDK.

El wheel de Studio también se instaló fuera del checkout: sus fuentes y bytes
instalados coinciden y repitió **13 pruebas de controlador/UI**, con guard offline.
Es una repetición del subconjunto ya contado, no 13 casos únicos adicionales.
[JUnit](studio-installed-junit.xml). La skill del repositorio y la personal
pasaron su validador; el scaffolder de la skill generó y ejecutó una aplicación
con los tres actores Python y un notebook nuevo. La skill anterior tiene
[copia de respaldo](skill-sync.json).

Ruff focal de los archivos nuevos y diff --check terminaron sin incidencias.
No se ejecutó CI remota ni se publicó ningún artefacto.
