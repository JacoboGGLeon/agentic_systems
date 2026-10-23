# Cierre local de Agentic Systems 2.1.3

La gramática única, el material de aprendizaje y la campaña final están
validados en el alcance descrito. **No se publicó, abrió PR, creó tag ni ejecutó
CI remoto**. La aceptación de release todavía requiere su revisión y CI.

## Qué puede mostrar el README

- **13 notebooks vigentes ejecutados offline**, con un import: `import agentic_systems as toolkit`.
- **49 programas de examples ejecutados**: 34 adaptaciones y 15 programas focalizados/integrados. Algunas adaptaciones solo preparan configuración o usan candidatos/jueces guardados, y así se identifican.
- **313 RunResult raíz offline observados**, con memoria de linaje y JSON completo por fuente. Son límites de ejecución, no aplicaciones independientes ni llamadas facturables.
- **75 escenarios finales online pasan**, incluidos controles Python, capacidades nativas y Studio; versiones, modelos y bytes están fijados en esta evidencia.

El [README de examples](../../../examples/README.md) demuestra `.lineage(...)`
y enlaza el [informe de RunResult y Lineage Memory](../../../docs/RUNRESULTS_LINEAGE_213.md).
El README principal enlaza este cierre. No se traslada certificación histórica
a la revisión actual ni se anuncia éxito universal de cualquier prompt.

## Todos los notebooks

Hay **42 archivos: 13 vigentes y 29 históricos/generados anteriores**. Los
históricos no se reejecutaron. El [inventario exhaustivo](../../../docs/NOTEBOOK_INVENTORY_213.md)
incluye los 42, gramática directa, elementos observados en RunResult, módulos
compartidos, configuración declarada, hashes y evidencia. El
[CSV de llamadas y parámetros](../../../docs/notebook_parameters_213.csv) y el
[JSON](../../../docs/notebook_inventory_213.json) permiten revisar el detalle.

| Notebook vigente | Gramática directa o compartida observada | Estado |
|---|---|---|
| [examples/agentic_systems_studio/notebooks/01_studio.ipynb](../../../examples/agentic_systems_studio/notebooks/01_studio.ipynb) | API compartida: Action, Agent, RunResult, Sequence, System, framework, runtime, skill, tool | Offline: pasa |
| [examples/api_walkthrough/01_api_user_guide.ipynb](../../../examples/api_walkthrough/01_api_user_guide.ipynb) | Action, Agent, Environment, Eval, Graph, Limits, Parallel, RunResult, Sequence, System, __version__, framework, load_skill, model_artifact, model_server, runtime, skill, tool | Offline: pasa |
| [tutorials/00_api.ipynb](../../../tutorials/00_api.ipynb) | Action, Agent, RunResult | Offline: pasa |
| [tutorials/01_tools_skills.ipynb](../../../tutorials/01_tools_skills.ipynb) | Action, Agent, RunResult, load_skill, skill, tool | Offline: pasa |
| [tutorials/02_agent_flows.ipynb](../../../tutorials/02_agent_flows.ipynb) | Action, Agent, Graph, Parallel, RunResult, Sequence, skill, tool | Offline: pasa |
| [tutorials/03_system_flows.ipynb](../../../tutorials/03_system_flows.ipynb) | Action, Agent, Graph, Parallel, RunResult, Sequence, System, skill, tool | Offline: pasa |
| [tutorials/04_environment.ipynb](../../../tutorials/04_environment.ipynb) | Action, Agent, Environment, RunResult, Sequence, System, skill, tool | Offline: pasa |
| [tutorials/05_eval.ipynb](../../../tutorials/05_eval.ipynb) | Action, Agent, Eval, RunResult, Sequence, skill, tool | Offline: pasa |
| [tutorials/06_runtime_framework.ipynb](../../../tutorials/06_runtime_framework.ipynb) | Action, Agent, RunResult, framework, runtime, skill, tool | Offline: pasa |
| [tutorials/07_results_limits.ipynb](../../../tutorials/07_results_limits.ipynb) | Action, Agent, Limits, RunResult, Sequence, skill, tool | Offline: pasa |
| [tutorials/08_model_serving.ipynb](../../../tutorials/08_model_serving.ipynb) | model_artifact, model_server | Offline: pasa |
| [tutorials/09_order_challenge.ipynb](../../../tutorials/09_order_challenge.ipynb) | API compartida: Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, skill, tool | Offline: pasa |
| [tutorials/10_contracts_judges.ipynb](../../../tutorials/10_contracts_judges.ipynb) | API compartida: Action, Agent, Environment, Eval, RunResult, framework, runtime, skill, tool | Offline: pasa |

El [nuevo notebook autónomo](../../../examples/api_walkthrough/01_api_user_guide.ipynb)
reúne la explicación completa: Tool/Skill/Action, seis flujos, run/compile/async,
límites, aprobación de pedidos, memoria, Eval, resultados, tipos, carga portable,
proveedores/frameworks y serving configurado. Sus 17 celdas de código no realizan
inferencia. La instrumentación y las guardas solo se añaden a las copias ejecutadas.

## Validación online del artefacto final

| Fase | Resultado | Evidencia |
|---|---:|---|
| matrix | 16/16 | [JSON](matrix.json) |
| features | 15/15 | [JSON](features.json) |
| integrated | 16/16 | [JSON](integrated.json) |
| studio | 16/16 | [JSON](studio.json) |
| studio-ui | 12/12 | [JSON](studio-ui.json) |

- Proveedores: Python determinista, Ollama `gemma4:31b-cloud`, Bedrock API key `qwen.qwen3-32b-v1:0` en us-east-2 y OpenAI `gpt-4.1-mini`.
- Frameworks: native, LangGraph, OpenAI Agents y Strands. [Identidades sin claves](routes.json).
- Matriz base: Tool certify con 37, serialización e invariantes; 16 combinaciones.
- Integrado: dos pedidos → quote determinista → actor del runtime seleccionado para approve/review → outputs exactos y memoria approved=1. Eval examina la ejecución guardada sin comprar otra ejecución; conserva los resultados y el linaje originales. Pasada final completa: 16/16.
- LangGraph: interrupt, InMemorySaver y Command resume reales, como extensión de aplicación dentro de Action.
- OpenAI Agents: handoff, callback, evento normalizado, SQLiteSession y control negativo de guardrail en cuatro proveedores.
- Strands: MCP Streamable HTTP y A2A JSON-RPC con servicios locales reales y agente remoto determinista; los clientes con proveedor externo sí usan inferencia.
- Interoperabilidad: cuatro actores en un System, con Python y con mezcla Python/OpenAI/Ollama/Bedrock; salida 46 e identidades conservadas.
- Studio backend: 16 combinaciones × tres turnos; recordar LINTERNA y calcular 17×19=323. Widgets AppTest: 12 combinaciones externas. No se afirma que los diez catálogos de razonamiento estén certificados live.

La [evidencia online con memoria de linaje](../../../docs/RUNRESULTS_LINEAGE_213.md#providers-y-frameworks-resultados-online-y-memoria)
separa cada caso y proveedor. Los notebooks continúan siendo offline.

## Fallos encontrados y corregidos

1. El example de conformidad fijaba 10 segundos, incluyendo carga inicial de SDKs bajo carga. El scheduler produjo un fallo explícito; el example declara ahora 60 segundos y conserva resultados en las aserciones. No se cambiaron defaults del SDK. [Registro reducido del fallo observado](offline-issue.json).
2. El límite del integrado aceptaba datos directos y el sobre simple `data`, pero rechazaba el ToolEnvelope completo de Bedrock native/LangGraph. La Tool había devuelto el total y estado correctos. Se reconocen sus campos estructurales y nombre de Tool, se extrae únicamente su data observada y se conserva el sobre original en los eventos.
3. Ese mismo límite lanzaba una excepción al rechazar evidencia y perdía el actor como hijo. Ahora devuelve el RunResult original con un error añadido, conservando datos, uso y eventos. Dos regresiones offline comprueban formatos de sobre y retención de fallos.

Los tres intentos online fallidos anteriores permanecen en el
[índice](failure-index.json) y sus directorios de intentos. El
[resultado diagnóstico](diagnostic-bedrock-result.json) conserva el ToolEnvelope
correcto y el rechazo del límite. La corrección está en la aplicación compartida
por notebook y campaña; no se cambió modelo, proveedor, framework ni wheel para aprobar.

## Resultados, tests y distribución

- SDK: **180 tests**, cobertura por sentencias de la API canónica nueva **100.00%** (1196 sentencias). El motor privado histórico no forma parte de ese porcentaje. [JUnit](tests.xml), [cobertura](coverage.json).
- Studio: **14 tests offline**; límite de evidencia de negocio: **2 regresiones**. [Studio](studio-offline-tests.xml), [regresiones](business-boundary-tests.xml).
- **13/13 notebooks**, **15/15 programas focalizados**, **34/34 adaptaciones** y proyecto generado con **14 contratos**. [Notebooks](notebooks.json), [examples](examples.json), [adaptaciones](adaptations.json), [proyecto](packaging.json).
- Wheel y fuente SDK: **116 archivos idénticos**; los mismos archivos están en el sdist. README embebido congelado y fuente coinciden. Import base mantiene SDKs opcionales lazy.
- Studio instalado: **21 archivos idénticos** al wheel, notebook y health local verificados. [Instalación](studio-install.json).
- Ruff, tres fronteras de arquitectura, escaneo de secretos y revisión de enlaces se ejecutan localmente. El workflow incorpora los 13 notebooks y los nuevos contratos.

## Presupuesto final

Asignación separada autorizada: **USD 10 / 300 llamadas**. Consumo reservado:
**238 llamadas / USD 9.673028**. Restan **62
llamadas / USD 0.326972** en el snapshot. Las reservas incluyen
fallos y diagnóstico, y no son facturación observada. Todos los trabajadores
de inferencia terminaron antes del cierre; los hooks siguieron activos durante
su vida. La asignación anterior permanece intacta, con 198 llamadas.

Se reservan bytes UTF-8 + 4096 como cota de input, salida máxima declarada y
25% de margen, a USD 5/M input y USD 20/M output. Los protocolos locales
registrados no se cuentan como inferencia. [Ledger](budget.json).
Intentos por fase: `{'matrix': 24, 'features': 24, 'integrated': 94, 'studio': 60, 'studio-ui': 36}`.

## Artefactos locales y pendientes

- [Wheel SDK](../closeout-artifacts/agentic_systems-2.1.3-py3-none-any.whl): `b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283`.
- [sdist SDK](../closeout-artifacts/agentic_systems-2.1.3.tar.gz): `88169951ced5c823bda436e15e227529f0133bd7efa422bf400f54e49e65b03f`.
- [Wheel Studio](../closeout-artifacts/agentic_systems_studio-2.1.3-py3-none-any.whl): `4aed36644d555e5a05f80da034645ed2dd9a6f100dccd224cddeef93a07adab4`.
- [Notebook descargable](../closeout-artifacts/01_api_user_guide.ipynb) · [Studio ZIP limpio](../closeout-artifacts/agentic-systems-studio-2.1.3-final-local.zip).
- [Manifiesto y hashes](manifest.json) · [Proyecto generado limpio](generated-project.zip).

No se incluyeron credenciales ni wheelhouse de dependencias en el ZIP.
Validación local en Python 3.14.2; runners CI y Python 3.10–3.13 siguen pendientes
de ejecución remota. vLLM/Colab GPU, AWS IAM y ADA IAM requieren sus entornos.
No se añadió [ada], ADA Studio ni wallet. El cierre local no equivale a publicación,
certificación empresarial ni garantía de cualquier versión futura de dependencias.
