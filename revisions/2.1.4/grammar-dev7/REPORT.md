# Graph y compilación · 2.1.4.dev7

Revisión local sin publicar. Graph define, compile prepara, run ejecuta y human_results explica. Agent organiza una capacidad; System coordina la aplicación; Environment procesa episodios. No hay check ni StateGraph como nombres públicos alternativos.

Wheel SHA-256: `f96d9fc165251e798374a1a9ed6b32e99c2704e210925acf6a579b06cd1a4f16`. [Wheel](builds/01/agentic_systems-2.1.4.dev7-py3-none-any.whl) · [sdist](builds/01/agentic_systems-2.1.4.dev7.tar.gz) · [Instalación](installation.json) · [Snapshot de fuente](source-snapshot.json). El commit identifica la base; los cambios locales quedan identificados por hashes.

Validación con Python **3.14.2**: **364 pruebas**, **28 notebooks** (22 tutorials + 6 examples), **56 entrypoints** y **1 example MCP/A2A local**. **15/15 palabras core** ejercitadas; cinco objetos originales de LangGraph se informan aparte. [JUnit](offline-junit.xml) · [Examples](examples-offline.json) · [Protocolos](local-protocols.json) · [Resumen](summary.json).

## Contratos

| Contrato | Evidencia |
| --- | --- |
| Graph único | Identidad con StateGraph original; no exports StateGraph ni check |
| compile prepara | Compilación sin efectos, records lazy ni casos ejecutados |
| Tools Pydantic | Binding modelo como nodo y en native/OpenAI Agents/Strands con Python; entradas/salidas inválidas rechazadas |
| SDK OpenAI | Contrato root sin envoltura de parámetro; validación de JSON crudo antes de efectos y sin coerción previa |
| Eval aislada | Cada caso tiene su vista de Memory; progreso por episodio interno y sin escritura de producción |
| human_results | Entradas anidadas reales, estados reales, operaciones semánticas y un ID raíz |
| Environment/rewards | Métrica explícita en update/state/history; no reward= ni entrenamiento implícito |
| Artefacto independiente | Wheel/sdist, instalación externa, 118 hashes RECORD y toda la validación ligada al hash |

## Lo que cambió

Graph es el StateGraph original de LangGraph bajo un único nombre público. Se retira check y su módulo del SDK. Los constructores conservan validación local; compile comprueba estructura declarada sin ejecutar negocio. No prueba código Python arbitrario.

Tools con input_schema y un único parámetro de negocio reciben el modelo Pydantic. Una firma contradictoria se rechaza antes de efectos; como nodo se proyectan los campos del contrato. OpenAI Agents antes generaba una envoltura request; el adaptador ahora expone el contrato raíz y valida argumentos JSON crudos antes del cuerpo, evitando coerción previa del SDK. Regresiones con SDKs reales prueban el mismo modelo Quantity directamente, como nodo y con native/OpenAI Agents/Strands sobre Python, incluidos negativos. No certifican todos los tipos Pydantic ni todos los proveedores live.

Eval da a cada caso vistas privadas de Memory, incluidos accesos por closures y comprobaciones. Un Environment del mismo caso observa sus episodios anteriores dentro de esa vista. No se escriben episodios en Memory de producción. Esto no clona sesiones SDK ni aísla efectos externos o archivos.

Las entradas de unidades anidadas se guardan como evidencia original. human_results usa estados reales, nombres de negocio y un solo ID raíz; oculta wrappers en esa presentación, manteniendo to_dict/trace/lineage completos. Las decisiones no se imprimen como status.

## Notebook y rewards

[Notebook explícito ejecutado](../../../examples/checked_composition/01_checked_composition.ipynb): input 5000 → fee 50 → total 5050 → approved; segundo pago 12000 → fee 120 → total 12120 → pending_review. Eval comprueba ambos y mantiene tres episodios en Memory de producción.

La recompensa se calcula explícitamente en Environment.update: 1 si la salida coincide con el oráculo del Environment, 0 si no. El oráculo no se pasa al System. State/history registran reward y total_reward=2. No hay reward= público ni entrenamiento automático de una política. [Contrato de Environment](../../../docs/ENVIRONMENT_214.md).

## Intentos y límites

La primera pasada de notebooks registró un timeout de 40 segundos en common_graph al ejecutarse junto a otros validadores. Se conserva ese intento y se repite el mismo notebook, con el mismo wheel, límites y oráculos, en un proceso aislado: pasó sus 16 celdas. No se relajó el plazo ni se atribuyó un PASS de otro caso. notebook-runs conserva todas las pasadas; el inventario toma la más reciente de cada archivo.

Los fallos iniciales de migración, el binding Pydantic OpenAI y los intentos fuente se conservan en source-*-junit.xml y logs. La suite de 364 tests contra el wheel instalado terminó sin fallos, errores ni skips.

El scaffolder de CLI/skill generó fuera del checkout un proyecto con Graph; se ejecutó con los tres actores Python y su notebook en un kernel nuevo. [Evidencia](scaffolder.json). Studio pasó su subconjunto de controlador/UI dentro de las 364 pruebas; no se afirma cobertura total de UI o modelos reales. MCP/A2A usó modelos fixture y transportes reales de loopback, con conexiones externas prohibidas y cierre de servicios.

**Cero inferencia y cero publicación.** La campaña dev5 conserva 148/150 solicitudes y USD 0.875040 reservados de USD 5, con hash inalterado. Artefactos dev5 y dev6 se conservan intactos. La aceptación live previa no se transfiere a dev7.

Quedan pendientes la campaña live del artefacto final, CI Python 3.10–3.14, Bedrock/null y Studio/Bedrock, interoperabilidad Ollama cloud, vLLM, AWS IAM/ADA IAM y persistencia durable. No se promete preempción forzosa, rollback ni una API RL completa.

[API](../../../docs/API_214.md) · [Firmas](../../../docs/API_214_SURFACE.md) · [Inventario](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults/Memory/linaje](../../../docs/RUNRESULTS_LINEAGE_214.md).

## Entregables y demostración capturada

[Notebook ejecutado: Agent → System → Environment y rewards](agent_system_environment_rewards.ipynb) ·
[Input → proceso → output y human_results literales](INPUT_PROCESS_OUTPUT.md) ·
[RunResults completos y observaciones de Memory](demonstration.json).

Los dos casos de Eval observaron tres episodios anteriores cada uno y la Memory
de producción quedó en tres: el aislamiento no es solo una instancia nueva
mostrada en el ejemplo; se aplica por caso en la ejecución de Eval.

[Studio wheel](bundles/agentic_systems_studio-2.1.4.dev7-py3-none-any.whl),
[skill](bundles/agentic-systems-skill-2.1.4.dev7.zip) y
[material de aprendizaje](bundles/agentic-systems-learning-2.1.4.dev7-r2.zip)
son entregables separados del SDK. [Hashes](bundles/hashes.json).
El ZIP didáctico inicial se conserva; r2 corrige una etiqueta Graph en la
cobertura generada, sin cambiar código ejecutado ni bytes del SDK.

El wheel independiente de Studio se instaló fuera del checkout y pasó otras
13 comprobaciones de controlador/UI, ya incluidas en los 364 casos únicos:
no se suman como casos nuevos. [JUnit](studio-installed-junit.xml).
La skill personal dev7 quedó sincronizada y validada con copia de respaldo de
la versión anterior; [registro](skill-sync.json). Ruff focal y diff --check
terminaron sin incidencias. Los logs y todos los intentos permanecen en esta
carpeta. No se ejecutó CI remota ni se publicó.
