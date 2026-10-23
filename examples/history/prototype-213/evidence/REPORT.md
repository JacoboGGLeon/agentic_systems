# Candidata 2.1.3: revisión de API y challenge offline

Python 3.14.2; Agentic Systems 2.1.2; LangGraph 1.2.16.

**12/12 combinaciones**, **4/4 ramas alternativas**, **79/79 pruebas offline**. Notebook ejecutado en un kernel nuevo: 20 celdas de código, sin errores. **Inferencia: 0 llamadas, USD 0**.

El wheel publicado de 2.1.2 se verificó byte por byte contra la instalación sin modo editable. SHA-256: `2c14a8e6f871fcc455acbf899db851130c49a129ba988821d6656e90ebc3d47b`.

## Input → proceso → output

| Propietario | Flujo | Backend | Input | Proceso observado | Output | Estado |
|---|---|---|---|---|---|---|
| Agent | sequential | native | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} | `{"value": 8}` | PASS |
| Agent | sequential | langgraph | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} | `{"value": 8}` | PASS |
| Agent | parallel | native | `{"value": 3}` | increase: {'value': 4} ; multiply: {'value': 6} → sumar salidas de ambas ramas | `{"value": 10}` | PASS |
| Agent | parallel | langgraph | `{"value": 3}` | increase: {'value': 4} ; multiply: {'value': 6} → sumar salidas de ambas ramas | `{"value": 10}` | PASS |
| Agent | graph | native | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} · ruta: increase → multiply, multiply → END | `{"value": 8}` | PASS |
| Agent | graph | langgraph | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} · ruta: increase → multiply, multiply → END | `{"value": 8}` | PASS |
| System | sequential | native | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} | `{"value": 8}` | PASS |
| System | sequential | langgraph | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} | `{"value": 8}` | PASS |
| System | parallel | native | `{"value": 3}` | increase: {'value': 4} ; multiply: {'value': 6} → sumar salidas de ambas ramas | `{"value": 10}` | PASS |
| System | parallel | langgraph | `{"value": 3}` | increase: {'value': 4} ; multiply: {'value': 6} → sumar salidas de ambas ramas | `{"value": 10}` | PASS |
| System | graph | native | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} · ruta: increase → multiply, multiply → END | `{"value": 8}` | PASS |
| System | graph | langgraph | `{"value": 3}` | increase: {'value': 4} → multiply: {'value': 8} · ruta: increase → multiply, multiply → END | `{"value": 8}` | PASS |

En paralelo, las ramas se muestran en orden declarado, no como cronología. Ambas reciben el mismo input de forma aislada. Los Systems coordinan Agents reales del prototipo con Skills propias, y conservan sus identidades.

Las decisiones se verificaron también con `−3 → incrementar: −2 → END → −2` en ambos propietarios y backends (4/4). Las pruebas incluyen el umbral `−1 → incrementar: 0 → duplicar: 0`: la condición recibe el resultado del paso previo.

## Decisiones y compatibilidad

- Una conexión acepta un destino fijo o una función directa: `('increase', choose_next)`. No se añadió otro constructor ni un builder encadenado.
- Los destinos directos válidos son los nodos del grafo y `END`; el valor elegido se valida al ejecutar y queda en `meta['next']`.
- `compile()` no ejecuta condiciones. LangGraph recibe el conjunto de nodos y END como destinos posibles; su dibujo puede sobreaproximar las rutas que una función concreta elige. No hay análisis del código de la condición.
- `Route(choose, targets)` conserva sus restricciones anteriores. Se contrastó con la forma directa en ambos propietarios y backends.
- Se verificaron destinos inválidos y excepciones conservando el resultado previo y sus eventos; también aislamiento, serialización, linaje y ciclos limitados.
- El paquete 2.1.2, sus 89 exports y contratos heredados permanecen intactos. Los cambios viven únicamente en el módulo experimental `unified_grammar`.

## Comprobaciones adicionales

- El notebook comprobó 16 ejecuciones preparadas y 16 contrastes contra el demo compartido. Los flujos LangGraph contienen `CompiledStateGraph` reales.
- El System integrado, los dos pasos de Environment y los dos casos de Eval determinista siguen pasando con los contratos reales de 2.1.2.
- El notebook conecta explícitamente las Skills con los Agents y reutiliza las mismas 12 unidades en Environment y Eval: 24/24 pasos y 24/24 casos en esa matriz adicional, con native y LangGraph.
- Los dos controles negativos de Eval detectaron expectativas incorrectas: la unidad devolvió 8 correctamente y Eval rechazó el valor esperado 999.
- Los ejemplos tuvieron 0 intentos de red/subprocesos. Los controles negativos de la suite verificaron que conexiones ordinarias y subprocesos siguen bloqueados.
- La salida de la suite mostró 13 avisos de deprecación del SDK sobre `asyncio.iscoroutinefunction`; no se alteró el SDK publicado.

## Skills, Environment y Eval: input → proceso → output

| Conexión | Input | Proceso observado | Output |
|---|---|---|---|
| Skills | valor 3 | Agent resuelve increment/double por nombre en su Skill arithmetic | valor 8 |
| Environment | registros 3 y −3 | mismo System con decisión por paso; conserva historia y memoria del episodio | valores 8 y −2; processed=2 |
| Eval | casos 3/−3 con expectativas 8/−2 | mismo System; comparación exacta de ok y data | 2/2 casos aprobados por backend |
| Eval: control negativo | valor 3, expectativa 999 | compara la salida real 8 con 999 | un fallo de evaluación esperado por backend |

La matriz adicional repite las conexiones sobre los seis ejemplos: para inputs 3/−3, secuencia produce 8/−4, paralelo 10/−8 y decisión 8/−2. Los resultados reales y el linaje quedan en `boundary_matrix` de la [evidencia del notebook](six-examples.json). Environment alimenta registros independientes; la memoria no se inyecta automáticamente en los Agents. Eval recibe el mismo Agent/System directamente. Se mantienen los wrappers síncronos existentes y una sola forma habitual de ejecución: `run()`.

## Entorno y límites

La primera ejecución restringida se detuvo por el bloqueo de localhost de Windows (`WinError 10013`). Jupyter y asyncio necesitaron permiso del sistema para su transporte local. La ejecución completada mantuvo el mismo guard de aplicación. Véase [registro de entorno](execution-environment.json). El fallo histórico anterior del guard también permanece separado en [tests-initial-guard.xml](tests-initial-guard.xml).

Esta es aceptación determinista del prototipo, no certificación de modelos ni de una nueva versión. No añade DAGs arbitrarios, cancelación forzosa ni checkpoint persistente. El guard pertenece al proceso Python, no es un sandbox del sistema operativo. Solo se verificaron las versiones indicadas.

[Notebook ejecutado](../00_walkthrough.ipynb) · [Evidencia del notebook](six-examples.json) · [Ejecución con wheel verificado](offline-run.json) · [Pruebas](tests.xml) · [Manifiesto](../manifest.json)

## Challenge realista: pedidos

Siete Agents, siete Skills y ocho Tools comparten una única declaración. Intake normaliza/valida en secuencia; Pricing e Inventory trabajan en paralelo; Policy y las funciones directas del grafo seleccionan aprobación, revisión o rechazo. Se usan únicamente fixtures locales y precios en centavos; no se ejecutan acciones externas.

| Backend | Caso | Input | Proceso | Output | Contrato |
|---|---|---|---|---|---|
| native | approve | PO-001 | normalize → validate → price → stock → assess → approve | `{"order_id": "PO-001", "decision": "approved", "total_cents": 75000, "currency": "MXN", "reasons": [], "next_action": "prepare_shipment"}` | PASS |
| native | budget | PO-002 | normalize → validate → price → stock → assess → reject | `{"order_id": "PO-002", "decision": "rejected", "total_cents": 75000, "currency": "MXN", "reasons": ["over_budget"], "next_action": "notify_customer"}` | PASS |
| native | stock | PO-003 | normalize → validate → price → stock → assess → reject | `{"order_id": "PO-003", "decision": "rejected", "total_cents": 1005000, "currency": "MXN", "reasons": ["insufficient_stock"], "next_action": "notify_customer"}` | PASS |
| native | review | PO-004 | normalize → validate → price → stock → assess → review | `{"order_id": "PO-004", "decision": "review", "total_cents": 255000, "currency": "MXN", "reasons": ["high_value_order"], "next_action": "request_human_approval"}` | PASS |
| native | invalid | PO-005 | normalize → validate → reject | `{"order_id": "PO-005", "decision": "rejected", "total_cents": null, "currency": "MXN", "reasons": ["invalid_quantity"], "next_action": "notify_customer"}` | PASS |
| native | duplicate_lines | PO-006 | normalize → validate → price → stock → assess → reject | `{"order_id": "PO-006", "decision": "rejected", "total_cents": 732000, "currency": "MXN", "reasons": ["insufficient_stock"], "next_action": "notify_customer"}` | PASS |
| native | inventory_failure | PO-007 | normalize → validate → price → stock | `{"ok": false, "completed_quote_retained": true}` | PASS |
| langgraph | approve | PO-001 | normalize → validate → price → stock → assess → approve | `{"order_id": "PO-001", "decision": "approved", "total_cents": 75000, "currency": "MXN", "reasons": [], "next_action": "prepare_shipment"}` | PASS |
| langgraph | budget | PO-002 | normalize → validate → price → stock → assess → reject | `{"order_id": "PO-002", "decision": "rejected", "total_cents": 75000, "currency": "MXN", "reasons": ["over_budget"], "next_action": "notify_customer"}` | PASS |
| langgraph | stock | PO-003 | normalize → validate → price → stock → assess → reject | `{"order_id": "PO-003", "decision": "rejected", "total_cents": 1005000, "currency": "MXN", "reasons": ["insufficient_stock"], "next_action": "notify_customer"}` | PASS |
| langgraph | review | PO-004 | normalize → validate → price → stock → assess → review | `{"order_id": "PO-004", "decision": "review", "total_cents": 255000, "currency": "MXN", "reasons": ["high_value_order"], "next_action": "request_human_approval"}` | PASS |
| langgraph | invalid | PO-005 | normalize → validate → reject | `{"order_id": "PO-005", "decision": "rejected", "total_cents": null, "currency": "MXN", "reasons": ["invalid_quantity"], "next_action": "notify_customer"}` | PASS |
| langgraph | duplicate_lines | PO-006 | normalize → validate → price → stock → assess → reject | `{"order_id": "PO-006", "decision": "rejected", "total_cents": 732000, "currency": "MXN", "reasons": ["insufficient_stock"], "next_action": "notify_customer"}` | PASS |
| langgraph | inventory_failure | PO-007 | normalize → validate → price → stock | `{"ok": false, "completed_quote_retained": true}` | PASS |

**14/14 contratos**: seis resultados de negocio y un fallo técnico esperado por backend. El fallo de inventario conserva la cotización terminada y evita ejecutar Policy o un agente terminal. Environment procesó seis pedidos y Eval aprobó seis casos por backend; los dos controles con un centavo de diferencia fueron detectados. Los SKU duplicados se agregan antes de comprobar stock. Inventario fijo por pedido; sin reservas entre pasos.

## Scaffolder completo y portabilidad

El [proyecto generado](agentic-systems-2.1.3-scaffold.zip) fue ejecutado fuera del repositorio: entrada con ambos backends, **12/12 pruebas** y notebook en kernel nuevo. Se verificaron sus hashes y los imports locales frente al wheel base sin modo editable. El generador rechaza destinos existentes y ubicaciones dentro de sus fuentes; esas condiciones forman parte de las 79 pruebas del prototipo.

La revisión objetivo es **2.1.3**; el SDK publicado y probado como baseline sigue siendo **2.1.2**. No se ha promovido la fachada al SDK ni publicado una nueva versión. Véanse [árbol completo](../../../docs/SCAFFOLDER_213.md), [fuente única](../order_challenge/system.py), [evidencia del challenge](challenge.json) y [aceptación del scaffolder](scaffold-smoke.json).
