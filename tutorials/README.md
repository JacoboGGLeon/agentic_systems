# Tutoriales

Esta carpeta es la ruta ejecutable y can?nica para aprender Agentic Systems 2.0.
Los notebooks ense?an la API p?blica y, cuando corresponde, las capacidades
reales de los SDK integrados. No contienen una segunda implementaci?n de la
librer?a.

## Promesa de uso

    instalar -> elegir capa -> abrir notebook -> Run All

Run All es el camino principal. Ning?n notebook depende de celdas secretas,
outputs guardados o mutaciones manuales de RunResult. Para forzar una sesi?n
completamente offline, inicia Jupyter con RUN_*_LIVE=0.

## Capas

| Capa | Pregunta que responde | Regla |
|---|---|---|
| core | ?C?mo se modela y compone un sistema ag?ntico? | Python Runtime, Framework Native y Graph portable. |
| providers | ?D?nde se ejecuta la inferencia? | Una ruta p?blica com?n; llamadas externas con preflight. |
| frameworks | ?Qui?n controla el agent loop? | SDK real offline y Provider auto opcional para live. |

Provider y Framework son ejes independientes:

    Agent -> Framework real -> modelo materializado -> Provider real -> RunResult

## Ruta recomendada

### Core

| Orden | Notebook | Evidencia |
|---:|---|---|
| 00 | core/00_runtime_scheduler.ipynb | Runtime Python, l?mites, retries y timeout. |
| 01 | core/01_tool.ipynb | Tool, schemas, policy y ejecuci?n directa. |
| 02 | core/02_skills.ipynb | Skill nativa, composici?n y carga SKILL.md + skill.py. |
| 03 | core/03_agent.ipynb | Agent, contrato, policy y RunResult. |
| 04 | core/04_results_lineage.ipynb | Vistas, composici?n y lineage desde resultados reales. |
| 05 | core/05_system.ipynb | Ownership, registros e inspecci?n est?tica. |
| 06 | core/06_graph_native.ipynb | Graph portable sin SDK externo. |
| 07 | core/07_environment_eval.ipynb | Episodios, rewards reproducibles y Eval. |
| 08 | core/08_single_agentic_system.ipynb | Sistema ag?ntico individual end-to-end. |
| 09 | core/09_multi_agentic_system.ipynb | Dos Agents y composici?n de evidencia. |
| 10 | core/10_multi_agent_graph.ipynb | Orquestaci?n multiagente con Graph portable. |

### Providers

| Orden | Notebook | Evidencia |
|---:|---|---|
| 00 | providers/00_auto.ipynb | Resoluci?n y diagn?stico sin ejecutar modelos. |
| 01 | providers/01_openai.ipynb | openai-runtime mediante la ruta p?blica com?n. |
| 02 | providers/02_bedrock.ipynb | bedrock-runtime por boto3 con SigV4 o bearer token. |
| 03 | providers/03_vllm.ipynb | vllm-runtime contra endpoint OpenAI-compatible. |

Bedrock no tiene dos Providers. Las credenciales AWS tradicionales y
AWS_BEARER_TOKEN_BEDROCK son dos formas de autenticar el mismo cliente boto3 y
la misma identidad bedrock-runtime.

### Frameworks

| Orden | Notebook | Evidencia |
|---:|---|---|
| 00 | frameworks/00_langgraph.ipynb | StateGraph real, routing, sync/async, native graph y lineage. |
| 01 | frameworks/01_openai_agents.ipynb | Runner, Tools mixtas, output tipado, sessions, guardrails y handoffs. |
| 02 | frameworks/02_aws_strands.ipynb | Agent, hooks, Tools mixtas, structured output y MCP stdio/HTTP. |

Los notebooks de Framework usan python-runtime por defecto para ejecutar el SDK
real sin red. RUN_LANGGRAPH_LIVE=1, RUN_OPENAI_AGENTS_LIVE=1 o
RUN_STRANDS_LIVE=1 cambia ?nicamente el Provider hacia la resoluci?n auto.

## Readiness externa

| Frontera | Configuraci?n | Opt-out |
|---|---|---|
| OpenAI | OPENAI_API_KEY; OPENAI_MODEL opcional | RUN_OPENAI_LIVE=0 |
| vLLM | VLLM_BASE_URL y VLLM_MODEL; token opcional | RUN_VLLM_LIVE=0 |
| Bedrock | regi?n y SigV4, rol/perfil o AWS_BEARER_TOKEN_BEDROCK | RUN_BEDROCK_LIVE=0 |
| Framework live | al menos un Provider externo listo | RUN_*_LIVE=0 |

Un skip de infraestructura nunca cuenta como evidencia live. Errores de
credenciales, permisos, modelo o endpoint permanecen visibles cuando live est?
activado.

## Contrato de salida

Los notebooks producen resultados mediante la API p?blica:

    toolkit.human_result(result)
    toolkit.show(result)
    toolkit.show_json(toolkit.run_result_output(result))

No construyen RunResult a mano, no alteran runtime/usage/validation y no
sustituyen Graph, Environment o Eval con loops locales.

## Gate de release

Los 18 notebooks deben:

1. importar agentic_systems as toolkit;
2. declarar objetivo, par?metros y api_coverage;
3. incluir metadata de layer, provider, framework y execution_mode;
4. compilar y empezar sin outputs persistidos;
5. respetar la frontera de API p?blica;
6. ejecutar top-to-bottom o producir un skip externo expl?cito.

La suite ejecuta 15 notebooks deterministas desde kernels limpios y valida
est?ticamente los 3 Providers externos.

## Contribution Standard

Every notebook must state its goal, editable inputs, ownership model, public API
construction, execution or explicit skip, human result, structured evidence,
limits and final api_coverage inventory. A top-to-bottom Run All must not depend
on hidden cells or fabricated results.

Tutorial code may define small domain fixtures and callbacks. It must not import
Agentic Systems package internals, duplicate package internals, replace public
contracts with hand-built dictionaries, use fake Providers to claim live
execution, or report an infrastructure skip as successful external evidence.

La construcci?n can?nica usa toolkit.tool(...), toolkit.skill(...),
toolkit.agent(...), toolkit.system(...), toolkit.graph(...),
toolkit.environment(...) y toolkit.eval(...).
