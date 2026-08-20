# Tutoriales

Esta carpeta es la ruta ejecutable y canónica para aprender Agentic Systems 2.0.
Los notebooks enseñan la API pública, no una segunda implementación de la
librería.

## Promesa de uso

    instalar -> configurar sólo si hay frontera externa -> abrir -> Run All

Ningún notebook depende de celdas secretas. Los notebooks Python canónicos
permanecen sin outputs; la evidencia se produce desde un kernel limpio.
Los notebooks paralelos de tutorials/cli preservan outputs Rich no secretos y
los regeneran con scripts/execute_cli_tutorials.py. RUN_*_LIVE=0 fuerza offline.

## Modelo que enseñan

    Tool / Skill -> Agent -> System -> Environment -> Eval
                          |
                          +-> Provider (dónde corre inferencia)
                          +-> Framework (quién controla el loop)
                          +-> RunResult (contrato de salida común)

En los ejemplos, `toolkit` es el alias de todo el paquete `agentic_systems`;
`ToolSet` es sólo un conjunto de Tools agrupadas bajo un namespace.

`toolkit.load_skill(path)` devuelve una Skill portable de Agentic Systems. Ese
formato reúne instrucciones, Tools y contratos, pero no afirma que cualquier
carpeta de Skill de Claude/Anthropic o ChatGPT/OpenAI sea intercambiable sin un
adaptador explícito.

Agent conserva su pipeline propio de una unidad de cómputo. `toolkit.agent(...)`
crea un System mínimo interno sólo para ownership, registros y defaults. System
compila un plan de ejecución externo que conecta y ordena unidades. Environment
añade episodios y pasos; Eval mide Agent, System o cualquier Executable.

## Orden pedagógico canónico

El orden conserva la progresión de 1.1.3. Los capítulos nuevos de 2.0 se
insertan donde aclaran Provider x Framework y cierran la trazabilidad 1:1.

| # | Notebook | Continuidad / evidencia |
|---:|---|---|
| 00 | providers/00_auto.ipynb | Runtime declarativo y resolución auto. |
| 01 | providers/02_bedrock.ipynb | Runtime Bedrock por la fachada común. |
| 02 | providers/01_openai.ipynb | Runtime OpenAI por la misma fachada. |
| 03 | core/00_runtime_scheduler.ipynb | Scheduler, retry y timeout. |
| 04 | providers/03_vllm.ipynb | Runtime vLLM OpenAI-compatible. |
| 05 | providers/04_ollama.ipynb | Runtime Ollama local OpenAI-compatible. |
| 06 | core/01_tool.ipynb | Tool, schemas y policy. |
| 07 | core/02_skills.ipynb | Skill nativa y carga desde filesystem. |
| 08 | core/03_agent.ipynb | Agent, contrato, pipeline y RunResult. |
| 09 | core/04_results_lineage.ipynb | Human result, composición y lineage. |
| 10 | frameworks/02_aws_strands.ipynb | Integración Strands real. |
| 11 | frameworks/01_openai_agents.ipynb | Integración OpenAI Agents real. |
| 12 | frameworks/00_langgraph.ipynb | LangGraph como lógica del Agent/System. |
| 13 | core/05_system.ipynb | Ownership, registros y compilación. |
| 14 | core/06_graph_native.ipynb | Graph portable sin SDK externo. |
| 15 | core/07_environment_eval.ipynb | Episodios, pasos, rewards y Eval. |
| 16 | core/08_single_agentic_system.ipynb | Sistema de un Agent end-to-end. |
| 17 | core/09_multi_agentic_system.ipynb | Sistema secuencial de varios Agents. |
| 18 | core/10_multi_agent_graph.ipynb | Sistema multi-agent con Graph. |
| 19 | frameworks/03_provider_framework_matrix.ipynb | Matriz 5 x 4 y evidencia live. |
| 20 | api/14_api_contract_matrix.ipynb | Contrato Source/API/Docs/CLI/Pytest 1:1. |

## Capas, no rutas separadas

| Capa | Pregunta | Regla |
|---|---|---|
| core | ¿Qué se construye y compone? | Python Runtime y Framework native. |
| providers | ¿Dónde corre inferencia? | Preflight; llamada externa sólo si está habilitada. |
| frameworks | ¿Quién controla el loop? | SDK real; Provider independiente. |
| api | ¿Todo lo publicado es trazable? | IDs exactos generados desde Source. |

## Auto, provider explícito y credenciales

Los notebooks específicos de Provider son explícitos: OpenAI, Bedrock,
vLLM u Ollama. Los notebooks de Framework usan python-runtime offline; al activar
live, auto elige el primer Provider listo según prioridad. La matriz 5 x 4 usa
cada Provider de forma explícita para que ninguna combinación quede oculta.

| Frontera | Configuración | Opt-out |
|---|---|---|
| OpenAI | OPENAI_API_KEY; OPENAI_MODEL opcional | RUN_OPENAI_LIVE=0 |
| Bedrock | región y cadena AWS o AWS_BEARER_TOKEN_BEDROCK | RUN_BEDROCK_LIVE=0 |
| vLLM | VLLM_BASE_URL y VLLM_MODEL | RUN_VLLM_LIVE=0 |
| Ollama | OLLAMA_MODEL; OLLAMA_BASE_URL opcional | RUN_OLLAMA_LIVE=0 |
| Matriz | RUN_MATRIX_LIVE=1 y Providers listos | RUN_MATRIX_LIVE=0 |

No pegues secretos en notebooks. Un caso no ejecutado se reporta como not-run
con motivo; nunca cuenta como passed. Un error live de credenciales, permisos,
modelo o endpoint permanece visible.

La matriz distingue estados que no deben confundirse:

| Estado | Significado |
|---|---|
| declared | La combinación pertenece al contrato 5 x 4. |
| ready | Su configuración y dependencias superaron el preflight. |
| not-run | No cruzó la frontera externa; incluye el motivo y no cuenta como éxito. |
| passed | Se ejecutó y sus invariantes fueron comprobados. |
| failed | Se ejecutó y preserva el error real. |

## Contrato de salida y narrativa

Cada demostración declara objetivo, parámetros editables, construcción,
ejecución o `not-run` explícito, resultado e interpretación y `api_coverage`.
La igualdad de `RunResult` significa el mismo esquema público y los mismos
invariantes en toda combinación; no significa que `data`, `final`,
`native_result`, `messages`, `usage`, `meta` o el objeto del SDK sean idénticos.
Los notebooks no fabrican resultados ni mutan sus campos para aparentar éxito.

## Gate de release

Los 21 notebooks Python deben importar agentic_systems as toolkit, usar sólo
la API pública estable, compilar, comenzar sin outputs y declarar metadata.
La suite los ejecuta desde kernels limpios: 17 producen evidencia determinista
y 4 prueban not-run de Providers. Los 21 notebooks CLI deben mapear 1:1, invocar
el CLI real y preservar salida Rich integra. El notebook API verifica
370 IDs y 10 escenarios compartidos.

## Contribution Standard

Every notebook must state its goal, editable inputs, ownership model, public API
construction, execution or explicit not-run, result interpretation and literal
api_coverage. Run All must not depend on hidden cells or fabricated results.

Tutorial fixtures may contain small domain callbacks, but must not import
package internals or duplicate provider/framework behavior. The canonical
grammar is toolkit.tool(...), toolkit.skill(...), toolkit.agent(...),
toolkit.system(...), toolkit.graph(...), toolkit.environment(...) and
toolkit.eval(...).
