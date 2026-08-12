# Tutoriales

Esta carpeta contiene la demostración ejecutable de Agentic Systems. Cada
notebook enseña una parte de la API pública desde la perspectiva de quien usa la
librería:

```python
import agentic_systems as toolkit
```

No existe una segunda implementación escondida en los tutoriales. Tools, Skills,
Agents, Systems, Graphs, Environments, Evals, resultados y presentación proceden
de la librería instalada.

## Promesa De Uso

```text
instalar -> configurar el Provider -> abrir el notebook -> Run All
```

**Run All es el camino principal.** Ningún notebook debe exigir celdas secretas,
un orden alternativo, mutaciones de resultados ni helpers locales que dupliquen
la API.

En notebooks con fronteras externas:

- un Provider listo ejecuta live por defecto;
- un Provider no configurado muestra un preflight accionable;
- `RUN_*_LIVE=0` desactiva deliberadamente una llamada;
- una ejecución real termina en `RunResult`;
- un skip nunca se presenta como evidencia live.

La configuración multiplataforma está en
[First Run Onboarding](../docs/ONBOARDING_FIRST_RUN.md).

## Ruta Conceptual

```text
Tool -> Skill -> Agent -> System -> Graph -> Environment -> Eval
```

Runtime, Provider, contratos, lineage y human output son capas transversales. La
construcción preferida usa una sola fachada:

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
| 0.1 | `00_runtime_api.ipynb` | Runtime, scheduler, perfiles y selección de Provider sin ejecutar modelos. |
| 0.2 | `00_runtime_bedrock_provider_api.ipynb` | Preflight AWS y ruta `runtime -> system -> agent -> RunResult`. |
| 0.3 | `00_runtime_openai_provider_api.ipynb` | Preflight OpenAI y la misma ruta pública de ejecución. |
| 0.4 | `00_runtime_scheduler_api.ipynb` | Límites, reintentos y timeout observables en el envelope. |
| 0.5 | `00_runtime_vllm_provider_api.ipynb` | Preflight OpenAI-compatible y la misma ruta pública. |
| 1 | `01_tool_api.ipynb` | Decorator/Pydantic, schemas y policy de Tools. |
| 2 | `02_skill_api.ipynb` | Composición de Tools, prompts, contracts, policy y metadata en una Skill. |
| 3 | `03_agent_api.ipynb` | Agent, runtime seleccionable, contrato, policy y `RunResult`. |
| 4 | `04_human_result_api.ipynb` | Proyecciones humanas y estructuradas del mismo resultado real. |
| 5 | `05_lineage_memory_api.ipynb` | Lineage y composición derivados de evidencia real. |
| 6 | `06_integrations_strands_api.ipynb` | Identidad Strands declarative-only sobre un Provider resuelto. |
| 7 | `07_integrations_openai_runtime_api.ipynb` | Identidad OpenAI Agents-style sobre el runtime seleccionado. |
| 8 | `08_system_api.ipynb` | Ownership, registros, Skills, Agents e inspección estática. |
| 9 | `09_graph_api.ipynb` | Estado y agent nodes con LangGraph opcional o backend portable. |
| 10 | `10_environment_eval_api.ipynb` | Episodios, reward contra un oracle independiente y Eval. |
| 11 | `11_single_agentic_system_api.ipynb` | System, Agent y Eval end-to-end con Provider seleccionable. |
| 12 | `12_multi_agentic_system_api.ipynb` | Dos Agents reales y composición de sus `RunResult`. |
| 13 | `13_multi_agentic_graph_api.ipynb` | Varios Agents reales orquestados con la API pública de Graph. |

## Readiness De Providers

| Provider | Configuración mínima | Opt-out |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `RUN_OPENAI_LIVE=0` |
| vLLM | `VLLM_BASE_URL` y `VLLM_MODEL` | `RUN_VLLM_LIVE=0` |
| Bedrock | Cadena AWS con credenciales utilizables | `RUN_BEDROCK_LIVE=0` |
| Strands identity | `provider="auto"` resuelve un Provider | `RUN_STRANDS_IDENTITY_LIVE=0` |
| OpenAI Agents-style | `provider="auto"` resuelve un Provider | `RUN_OPENAI_STYLE_LIVE=0` |

Inicia Jupyter desde la terminal que contiene las variables para que el kernel
las herede. Los notebooks no imprimen secretos; usa diagnósticos seguros:

```python
toolkit.show(
    toolkit.runtime(provider="auto").describe(),
    title="Resolved provider",
)
```

## Contrato De Salida

La presentación también pertenece a la API:

```python
toolkit.human_result(result)
toolkit.show(result)
toolkit.show_json(toolkit.run_result_output(result))
```

Los notebooks no definen `show_json`, no fabrican `RunResult`, no mutan sus
campos y no reemplazan Graph/Environment/Eval con loops locales.

## Gate De Release

Los 18 notebooks deben importar la fachada pública, empezar sin outputs
persistidos, compilar, declarar parámetros editables y `api_coverage`, y poder
ejecutarse de arriba abajo. El gate automático ejecuta los 13 deterministas
desde kernels limpios y valida estáticamente los 5 que dependen de Providers.
La ejecución live solo se afirma cuando existe evidencia de haber cruzado esa
frontera.

El estándar de contribución y el contrato Run All viven en este mismo documento.
La evidencia publicada está en
[GitHub Releases](https://github.com/JacoboGGLeon/agentic_systems/releases).

## Contribution Standard

Every notebook must state its goal, editable inputs, ownership model, public API
construction, execution or explicit skip, human result, structured evidence,
limits and final `api_coverage` inventory. A top-to-bottom Run All must not depend
on hidden cells or fabricated results.

Tutorial code may define small domain fixtures and callbacks. It must not import
package internals, replace public contracts with hand-built dictionaries, use
fake Providers to claim live execution, or report an infrastructure skip as a
successful external run.
