> Revisión histórica dev7. Para la aceptación local actual consulta el [informe dev8](../revisions/2.1.4/grammar-dev8/REPORT.md) y el [inventario vigente](NOTEBOOK_INVENTORY_214.md).

# Revisión de examples · 2.1.4.dev7

La revisión adicional ejecutó **57 entrypoints** y los **siete notebooks de
examples** con el wheel dev7 instalado fuera del checkout, sin inferencia.
Studio conserva una celda de servicio local omitida; MCP/A2A no se repitió y
permanece en su perfil separado. La revisión estática abarca 100 archivos Python,
79 Markdown y siete notebooks activos, incluidos infraestructura y tests de
Studio. No se confunde esa inspección con ejecutar toda la aplicación o sus tests.

[Evidencia por archivo](../revisions/2.1.4/grammar-dev7/examples-review/REPORT.md) ·
[Hashes y resultados](../revisions/2.1.4/grammar-dev7/examples-review/SUMMARY.json) ·
[Inventario estático completo](../revisions/2.1.4/grammar-dev7/examples-review/inventory.json).

## Qué cambió

| Área | Hallazgo | Acción |
|---|---|---|
| Lineage y Memory | El ejemplo ya demostraba cambios de decisión, pero faltaba seguirlos entre episodios y evaluaciones. | El [notebook de pagos](../examples/lineage_memory/01_lineage_memory_decisions.ipynb) añade Environment y Eval explícitos, Context completos y human_results. Pasó sus 18 celdas sin omisiones. |
| Context/Memory introductorio | El contador de episodios se añadía al estado del pedido. | El programa y el notebook lo observan aparte; el estado conserva datos de negocio. Ambos se volvieron a ejecutar. |
| README de ejemplos | Muchos empezaban importando run de otro módulo y enlazaban evidencia dev4 como si fuera la vigente. | Se enlazan las declaraciones visibles y la evidencia nueva cuando existe una pasada correcta del archivo concreto. Los informes viejos se conservan. |
| Versiones | Algunos módulos decían dev4, Studio pedía dev6 y había descripciones native/LangGraph ambiguas. | Se alinearon referencias actuales con dev7 y la separación entre actores y orquestación. |
| Episode Memory | La explicación mezclaba acumulación de estado con memoria episódica. | Se explica que sumar 2 y 3 es estado del Environment; Memory registra ejecuciones. Se enlaza el ejemplo que sí usa memoria para decidir. |
| Catálogo e inventario | El notebook nuevo no figuraba en el inventario de métodos/parámetros. | Se añadieron su cobertura y evidencia, y se actualizaron las entradas de notebooks ejecutados. |

No se detectaron usos de atributos públicos retirados mediante los alias de
agentic_systems en el código activo inspeccionado ni errores de sintaxis. Eso
no demuestra cobertura de todos los parámetros ni corrección semántica de cada
aplicación. La importación entre ejemplos que queda en order_fulfillment/run.py
es un lanzador, no la composición didáctica; Studio importa infraestructura del
perfil MCP/A2A y un test reutiliza una fixture de otro ejemplo.

## Qué demuestra ahora el notebook de pagos

1. El mismo PAY-001 pasa de approve a review_duplicate por Memory.
2. Sin Memory vuelve a approve; sin linaje actual o con comisión inconsistente,
   el revisor falla. El linaje participa realmente en la autorización.
3. Environment procesa PAY-002 dos veces y obtiene approve/review_duplicate.
   Memory tiene capacidad dos: sus IDs cambian después de cada episodio aunque
   la longitud no crezca. update calcula reward y total_reward termina en dos;
   es una métrica explícita, no entrenamiento automático.
4. Eval ejecuta dos casos del Environment con PAY-003 repetido. Dentro de cada
   caso se conserva progreso entre sus dos episodios. Ambos casos parten de los
   mismos IDs de producción, sus escrituras privadas tienen IDs distintos y
   Memory.read() es exactamente igual antes y después de Eval.
5. Los checks que capturan Memory por cierre también ven la vista aislada.
   Las listas externas de auditoría siguen acumulando observaciones: Eval no
   es un sandbox general para variables, archivos, clientes o servicios.

## Qué actualizar después, sin multiplicar ejemplos equivalentes

| Prioridad | Ejemplos existentes | Mejora concreta |
|---|---|---|
| Alta | common_graph, grammar_tour, unified_grammar, flow_semantics | Mantener un recorrido principal de los seis flujos y presentar los otros como referencias por objetivo, no cuatro puntos de entrada equivalentes. Conservar sus pruebas y artefactos. |
| Alta | context_memory_lineage, episode_memory, lineage_memory | Ruta clara: información del dominio → estado del episodio → evidencia que cambia decisiones → aislamiento de Eval. No llamar memoria a cualquier acumulador. |
| Alta | validation/aws_iam, ada_iam, vllm_colab, model_serving | Mantener visible configuration-only. La ejecución offline no certifica credenciales, GPU ni serving real. |
| Media | README con narrativas genéricas de input/proceso/output | Sustituir el texto genérico restante por el input concreto, la regla de negocio y un control negativo del propio ejemplo. La revisión actual corrige versiones y evidencia; no reescribe toda la narrativa de cada dominio. |
| Media | Studio y protocolos | Conservar la separación entre ejemplo mínimo explícito, controlador completo, UI y perfil local MCP/A2A. No anunciar todo Studio validado por ejecutar una conversación mínima. |

## Nuevos ejemplos que sí aportarían cobertura

| Prioridad | Ejemplo propuesto | Qué debe demostrar | Estado |
|---|---|---|---|
| 1 | Evidencia incompleta y memoria expulsada | Al alcanzar capacidad o truncar un resumen, no confundir ausencia de evidencia con ausencia del hecho; política explícita de revisión o consulta a un registro durable. | Propuesto; no implementado |
| 1 | Ramas paralelas con Context | Dos Agents reciben los antecedentes comunes, sin usar resultados de una rama hermana como si ya fueran antecedentes; unión y linaje verificables. Hay regresiones, falta una lección enfocada. | Propuesto; no implementado |
| 2 | Aprobación humana con pausa/reanudación | Mostrar el punto de pausa, el trabajo ya completado, Memory antes/después y cómo evitar repetir efectos. Reanudación en el mismo proceso, sin prometer recuperación durable. | Ampliar execution_lifecycle/common_graph |
| 2 | Contratos de entrada y proyección entre Agents | Un Agent produce información amplia; el siguiente recibe solo su contrato Pydantic. Datos ausentes o incorrectos fallan sin defaults que los oculten. | Ampliar tool_contracts/checked_composition |

Los nuevos ejemplos pueden empezar con Python determinista. Las variantes con
modelos y servicios necesitan su campaña y presupuesto propios. No hace falta
añadir constructores ni nuevas palabras públicas para las cuatro propuestas.

El código del SDK y su wheel permanecen iguales. No se publicó. Esta evidencia
es de aprendizaje offline y no sustituye la aceptación live pendiente del release.
