# Notebook Walkthrough Map

Los notebooks activos viven en `tutorials/`. Esta carpeta queda solo como indice historico/auxiliar para ubicarlos desde editores que agrupan notebooks.

## Orden Activo

| Orden | Notebook | Que cubre |
|---:|---|---|
| 0.1 | `../00_runtime_api.ipynb` | Runtime base y auto provider. |
| 0.2 | `../00_runtime_bedrock_provider_api.ipynb` | Bedrock Runtime provider. |
| 0.3 | `../00_runtime_openai_provider_api.ipynb` | OpenAI Runtime provider. |
| 0.4 | `../00_runtime_scheduler_api.ipynb` | Scheduler. |
| 1 | `../01_tool_api.ipynb` | Tools. |
| 2 | `../02_skill_api.ipynb` | Skills. |
| 3 | `../03_agent_api.ipynb` | Agents. |
| 4 | `../04_human_result_api.ipynb` | Human result. |
| 5 | `../05_lineage_memory_api.ipynb` | Lineage Memory. |
| 6 | `../06_integrations_strands_api.ipynb` | Strands integration. |
| 7 | `../07_integrations_openai_runtime_api.ipynb` | OpenAI Runtime integration. |
| 8 | `../08_system_api.ipynb` | System. |
| 9 | `../09_graph_api.ipynb` | Graph. |
| 10 | `../10_environment_eval_api.ipynb` | Environment + eval. |

## Regla

```python
import agentic_systems as lab
lab.runtime(provider="auto")
```
