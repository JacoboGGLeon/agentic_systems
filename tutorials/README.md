# Tutorials

Esta carpeta es la demostracion ejecutable de Agentic Systems. Cada notebook
ensena una parte de la API publica desde la perspectiva del usuario:

```python
import agentic_systems as toolkit
```

No hay una segunda implementacion escondida en los tutoriales. Tools, Skills,
Agents, Systems, Graphs, Environments, Evals, resultados y presentacion salen de
la libreria instalada.

## Promesa De Uso

```text
instalar -> configurar el Provider -> abrir el notebook -> Run All
```

**Run All es el camino principal.** Un notebook no debe exigir celdas secretas,
orden manual alternativo, mutaciones de resultados ni helpers locales que
dupliquen la API.

En notebooks externos:

- un Provider listo ejecuta live por defecto;
- un Provider no configurado muestra un preflight accionable;
- `RUN_*_LIVE=0` desactiva deliberadamente una llamada;
- una ejecucion real termina en `RunResult`;
- un skip nunca se presenta como evidencia live.

La configuracion completa para Git Bash esta en
[First Run Onboarding](../docs/ONBOARDING_FIRST_RUN.md).

## Ruta Conceptual

```text
Tool -> Skill -> Agent -> System -> Graph -> Environment -> Eval
```

Runtime, Provider, contratos, lineage y human output son capas transversales.
La construccion preferida usa una sola fachada:

```python
toolkit.tool(...)
toolkit.skill(...)
toolkit.agent(...)
toolkit.system(...)
toolkit.graph(...)
toolkit.environment(...)
toolkit.eval(...)
```

## Orden Recomendado

| Orden | Notebook | Aprendizaje observable |
|---:|---|---|
| 0.1 | `00_runtime_api.ipynb` | Declarar runtime, scheduler, profiles y seleccion de Provider sin ejecutar modelos. |
| 0.2 | `00_runtime_bedrock_provider_api.ipynb` | Preflight AWS y ruta `runtime -> system -> agent -> RunResult`. |
| 0.3 | `00_runtime_openai_provider_api.ipynb` | Preflight OpenAI y la misma ruta publica de ejecucion. |
| 0.4 | `00_runtime_scheduler_api.ipynb` | Limites, retry y timeout observables en el envelope. |
| 0.5 | `00_runtime_vllm_provider_api.ipynb` | Preflight del endpoint OpenAI-compatible y la misma ruta publica. |
| 1 | `01_tool_api.ipynb` | Declaracion decorator/Pydantic, schemas y policy de Tools. |
| 2 | `02_skill_api.ipynb` | Composicion de Tools, prompts, contracts, policy y metadata en una Skill. |
| 3 | `03_agent_api.ipynb` | Agent, runtime seleccionable, contrato, policy y `RunResult`. |
| 4 | `04_human_result_api.ipynb` | Proyecciones humanas y estructuradas del mismo resultado real. |
| 5 | `05_lineage_memory_api.ipynb` | Lineage y composicion derivados de evidencia real. |
| 6 | `06_integrations_strands_api.ipynb` | Identidad Strands declarative-only sobre un Provider resuelto. |
| 7 | `07_integrations_openai_runtime_api.ipynb` | Identidad OpenAI Agents-style sobre el runtime seleccionado. |
| 8 | `08_system_api.ipynb` | Ownership, registros, Skills, Agents e inspeccion estatica del System. |
| 9 | `09_graph_api.ipynb` | Estado y agent nodes con LangGraph opcional o backend portable. |
| 10 | `10_environment_eval_api.ipynb` | Episodios reales, reward contra oracle independiente y Eval. |
| 11 | `11_single_agentic_system_api.ipynb` | System, Agent y Eval end-to-end con Provider seleccionable. |
| 12 | `12_multi_agentic_system_api.ipynb` | Dos Agents reales y composicion de sus `RunResult`. |
| 13 | `13_multi_agentic_graph_api.ipynb` | Multiples Agents reales orquestados con la API publica de Graph. |

## Readiness De Providers

| Provider | Configuracion minima | Opt-out |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `RUN_OPENAI_LIVE=0` |
| vLLM | `VLLM_BASE_URL` y `VLLM_MODEL` | `RUN_VLLM_LIVE=0` |
| Bedrock | Cadena AWS con credenciales utilizables | `RUN_BEDROCK_LIVE=0` |
| Strands identity | `provider="auto"` resuelve un Provider | `RUN_STRANDS_IDENTITY_LIVE=0` |
| OpenAI Agents-style | `provider="auto"` resuelve un Provider | `RUN_OPENAI_STYLE_LIVE=0` |

Inicia Jupyter desde la misma terminal que contiene las variables:

```bash
python -m jupyter lab
```

Los notebooks no imprimen secretos. Usa diagnosticos seguros para confirmar la
resolucion:

```python
toolkit.show(
    toolkit.runtime(provider="auto").describe(),
    title="Resolved provider",
)
```

## Contrato De Salida

La presentacion tambien pertenece a la API:

```python
toolkit.human_result(result)
toolkit.show(result)
toolkit.show_json(toolkit.run_result_output(result))
```

Los notebooks no definen `show_json`, no fabrican `RunResult`, no mutan sus
campos y no reemplazan Graph/Environment/Eval con loops locales.

## Gate De Release

Los 18 notebooks deben:

- importar `agentic_systems as toolkit`;
- iniciar sin outputs persistidos;
- compilar todas sus celdas;
- declarar parametros editables y `api_coverage`;
- ejecutar de arriba hacia abajo con Run All;
- usar la ruta publica correspondiente;
- separar Provider ejecutable de identidad Framework;
- distinguir `pass`, `explicit skip` y `fail`;
- evitar SDKs directos, resultados fabricados y fallbacks manuales.

El estándar normativo vive en
[Tutorial Quality Standard](../docs/TUTORIAL_QUALITY_STANDARD.md). La evidencia
manual y automatizada se registra en
[Release 1.1](../docs/RELEASE_1_1.md).