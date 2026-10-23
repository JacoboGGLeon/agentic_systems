# Cómo enseñar y comprobar toda la gramática 2.1.3

Fecha: 2026-10-22. **Plan; no crea nuevos notebooks ni ejecuta inferencia.**
La [disposición de API](API_213_DISPOSITION.md) es una propuesta: los ejemplos
de sus extensiones aún no son código ejecutable del wheel existente.

## Qué acredita el material actual

Hay diez tutoriales ejecutados offline y un ejemplo de pedidos migrado a la
candidata. De las 36 entradas del catálogo, dos están marcadas como 2.1.3: la
aplicación y la referencia al curso. Eso no significa 36 implementaciones de
la API nueva. El catálogo histórico mantiene sus veredictos y versiones.

La matriz estática real está en `coverage` dentro del
[inventario JSON](api_inventory_213/inventory.json): archivo, celda, línea,
referencias, llamadas y keywords explícitos. Una llamada detectada no prueba
que se haya ejecutado ni que su resultado tenga una aserción; las referencias
ambiguas a métodos no se convierten en aceptación automática. El informe de
ejecución existente acredita solamente el wheel y alcance que identifica.

## Tutorial principal de cada palabra

Se conserva el curso actual y se completan sus capítulos. Solo se propone un
capítulo adicional, 10, para contratos y evaluación de modelos. No hace falta
un notebook nuevo por cada parámetro.

| Palabra / objeto | Tutorial principal | Cobertura actual | Completar dentro del mismo recorrido | Ejemplo propuesto |
|---|---|---|---|---|
| `tool` y Tool | 01 | Decoración y uso indirecto en Agent | run/arun/inspect; esquemas de entrada y salida; tipos inválidos, errores, JSON y evento | `tool_contracts/` |
| `skill` y Skill | 01 | Agrupación de Tools | Instructions, identidad/version/metadata, inspección; colisiones y propiedad por Agent | `portable_skills/` |
| `load_skill` | 01 | Carpeta temporal con build_skill | Carpeta portable real, imports relativos, ruta exacta; faltantes, retorno incorrecto y keyword desconocido | `portable_skills/` |
| `Action` | 02 | Nombre de Tool; input mapping en pedidos | Función, Tool y referencia a Skill; transformación; errores y ausencia de side effects al compilar | `flow_semantics/` |
| `Agent` | 02 + 06 | Tres flujos y actor Python | Mismo lifecycle por ambos modos; opciones incompatibles; Agents anidados; modelo explícito configurado sin llamarlo | `flow_semantics/`, `provider_framework_conformance/` |
| `System` | 03 | Tres flujos de varios Agents | Systems anidados, Action directo, ownership de Skills, fallo de hijo y preservación de identidad | `flow_semantics/` |
| `Sequence` | 02/03 | Flujo positivo y decisiones alternativas | Sustitución de estado, fallo intermedio, sin ejecutar pasos posteriores | `flow_semantics/` |
| `Parallel` | 02/03 | Fork/join y fallo de inventario | Copias independientes, nombres únicos, join una vez, fallo de join, resultados de todas las ramas completadas | `flow_semantics/` |
| `Graph` | 02/03 | Destino fijo, función y END | Ciclos, max_visits, nodo inexistente, función que falla, END inicial inválido; paridad native/LangGraph | `flow_semantics/` |
| `Environment` | 04 | Registros independientes, history y processed | Episodio nuevo por run; max_steps/truncación; compile/arun/inspect. Memoria, observe/update/stop solo después de implementar su contrato | `episode_memory/` |
| `Eval` | 05 + 10 | ok/data exactos y negativo | Checks personalizados, casos vacíos/vacuos, errores de check; juez y rúbrica con fixture offline; luego validación live separada | `evaluation_checks/` |
| `Limits` | 07 | max_actions positivo y agotado | Timeout cooperativo con reloj simulado, presupuesto compartido entre ramas/unidades, valores inválidos; no prometer cancelación fuerte | `execution_lifecycle/` |
| `RunResult`, eventos e incidencias | 07 | data/ok, JSON, walk y parentesco | Todos los campos, trace, lineage, invariantes; fallos, uso separado y secretos ausentes; un esquema de intercambio | `results_lineage/` |
| `runtime` y configuración retornada | 06 | Python ejecutado; otros cuatro declarados | Cada parámetro, cinco proveedores, valores inválidos, límites del actor, IAM/bearer documentado; inspección sin secretos | `provider_framework_conformance/` |
| `framework` y configuración retornada | 06 | Cuatro frameworks con Python | agent_kwargs/run_kwargs, claves reservadas, forwarding sin reemplazar límites, combinación no soportada | `provider_framework_conformance/` |
| `model_artifact` | 08 | Identificador básico | Cada campo: base/adaptador/tokenizer/revisión/cuantización/metadatos; inspección y validación | `model_serving/` |
| `model_server` y recurso retornado | 08 | Declarar e inspeccionar | Todos los keywords explícitos, precedencia de profiles, command redacted, start/health/stop con proceso/HTTP simulados | `model_serving/` |
| `__version__` y CLI | 00 | Versión, inventario de nombres | version/api/doctor/new, destinos existentes, wheel no editable, recursos empaquetados, import sin SDKs opcionales | `package_install/` |

El capítulo 09 sigue siendo la integración realista de pedidos. Debe enlazar
las piezas a los capítulos anteriores y mostrar input → proceso → output con
evidencia de Tools, decisiones, eventos y errores. No debe volver a copiar el
motor ni declarar otra gramática.

## Matriz de métodos y parámetros: criterio exigible

| Tipo de fila del inventario | Evidencia mínima para conservarla |
|---|---|
| Constructor / función | Una construcción válida y una inválida relevante; ningún proveedor ni callback creado durante compile/inspect |
| Parámetro | Identificador estable del parámetro; ejemplo explícito no-default o prueba de su default; verificación del efecto observable y de valores inválidos cuando tengan restricciones |
| Método ejecutor | Input y output con aserción; mismos datos finales para ejecución directa/compilada y sync/async donde se soporta |
| Método de lectura | Objeto de entrada conocido; salida verificable, sin mutar el objeto ni exponer secretos |
| Campo de resultado | Tipo, semántica, origen, presencia/ausencia y representación JSON; no basta imprimir todo el objeto |
| Mapa cerrado | Lista de claves, tipos, defaults y claves mutuamente excluyentes; clave desconocida rechazada |
| Opciones nativas de SDK | Ejemplo acotado por SDK/versión, forwarding comprobado y error para claves propiedad del toolkit; no afirmar portabilidad universal |
| Entrada retirada | Regresión de import, atributo o parámetro rechazado; no alias ni shim; explicar el destino canónico en migración |
| Dato / método de dependencia | Enumerado para detectar fugas; marcado como detalle interno, no enseñado como otra API de usuario |

Cada fila conservada tendrá `tutorial_ref`, `example_ref`, `test_ref`,
`execution_evidence_ref`, `artifact_sha256` y un estado. Estos enlaces de
aceptación son **trabajo futuro**: el auditor actual solo registra referencias
estáticas, firmas y objetivos por familia. No asigna automáticamente el estado
«cubierto» a todos los parámetros de una función porque su nombre aparezca.

Los estados deben ser distintos: `planned`, `implemented-not-run`,
`offline-verified`, `configured-only`, `live-verified`, `pending-environment`,
`retired`. Una fila con varias rutas puede tener un estado por ruta.
Estos estados se proponen para la futura matriz; no se reescriben las etiquetas
históricas del catálogo en este trabajo.

## Organización de examples/

Los siguientes nombres son destinos propuestos. Solo `order_fulfillment/`
existe hoy como implementación canónica del SDK nuevo.

```text
examples/
  README.md                     # índice por capacidad, versión y estado
  catalog.json                  # fuente de verdad; no duplicar implementación
  order_fulfillment/            # integración existente
  tool_contracts/               # operaciones y contratos
  portable_skills/              # carpeta de Skill realmente cargable
  flow_semantics/               # seis combinaciones Agent/System × flujo
  execution_lifecycle/          # run/arun/compile/inspect y límites
  results_lineage/              # trazabilidad, eventos, serialización, fallos
  episode_memory/               # episodios y memoria; implementación pendiente
  evaluation_checks/            # checks y fixture de juez, sin inferencia
  provider_framework_conformance/ # configuración y conformance por ruta
  model_serving/                # proceso simulado; GPU real separado
  package_install/              # instalación y scaffolder
  history/                      # material anterior, con versión y evidencia
```

Cada ejemplo contiene una sola declaración del sistema, fixtures sintéticos,
casos esperados, runner, tests y evidencia generada al ejecutar. Los tutoriales
pueden importarlo. El scaffolder copia esa misma fuente; no mantiene otro
constructor del sistema. La evidencia especifica versiones, backend, framework,
proveedor, modelo cuando exista, hash de wheel, intentos y resultado.

Las 34 referencias que no están migradas conservan sus estados originales.
Cada una necesita una decisión explícita: migrar al ejemplo canónico que ya
cubre su capacidad, mantener como histórico o retirar. No se suman como 34
ejemplos actuales por cambiarles un README o una etiqueta de versión.

## Fases de validación y brechas de release

1. **Ahora:** inventario y diseño estáticos. No se cambia ni se vuelve a
   certificar el wheel. No se ejecutan modelos, servidores ni Skills cargadas.
2. **Implementación offline futura:** un nuevo wheel; pruebas focalizadas de
   cada decisión, seis flujos con native/LangGraph, compilación pura,
   async, límites, memoria y checks. Los procesos/HTTP/jueces son simulados
   explícitamente cuando se necesitan; no cuentan como proveedores verificados.
3. **Curso y ejemplos:** ejecutar todos los notebooks y ejemplos fuera del
   repositorio, contra ese wheel no editable; enlazar filas a aserciones y
   evidencia. Verificar también el scaffolder generado y Python soportados.
4. **Proveedores reales:** fase posterior con autorización y presupuesto
   explícitos. Conservar la identidad de proveedor/framework/modelo y todos los
   fallos. Python Runtime no acredita OpenAI, Ollama, Bedrock o vLLM reales.
5. **Entornos externos:** vLLM/Colab GPU, AWS IAM y ADA IAM, cada uno con
   instrucciones propias y el mismo artefacto. Un test local no los acredita.
6. **Release:** API/docs/CLI/skill/Studio alineados, CI y checks de distribución.
   No publicar si una capacidad anunciada como conservada no tiene equivalente
   implementado y probado. Toda modificación de software requiere su propio
   artefacto y evidencia; este inventario no autoriza inferencia ni publicación.
