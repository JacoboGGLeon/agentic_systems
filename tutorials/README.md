# Tutorials

`tutorials/` es la ruta pedagogica oficial del repo.

```text
tutorials -> explora y explota la API 1:1
```

## Ruta Conceptual

La secuencia sigue el manifiesto de Agentic Systems:

```text
Tool -> Skill -> Agent -> System / Graph -> Environment -> Eval
```

Y usa estas capas transversales durante el recorrido:

```text
Memory / Lineage -> Runtime -> Provider -> Integrations
```

## Orden

| Orden | Notebook | Que cubre |
|---:|---|---|
| 0.1 | `00_runtime_api.ipynb` | Runtime base y `provider="auto"`. |
| 0.2 | `00_runtime_bedrock_provider_api.ipynb` | Bedrock Runtime: AWS diagnostics, Converse y embeddings. |
| 0.3 | `00_runtime_openai_provider_api.ipynb` | OpenAI Runtime: provider nativo directo; la integracion `openai-agents` se declara como framework cuando aplica. |
| 0.4 | `00_runtime_scheduler_api.ipynb` | Scheduler, budgets, retries y timeout. |
| 1 | `01_tool_api.ipynb` | Tool API e IO estructurado. |
| 2 | `02_skill_api.ipynb` | Skill API: tools, prompts, contracts, policy y metadata. |
| 3 | `03_agent_api.ipynb` | Agent API: contexto transformado en acciones. |
| 4 | `04_human_result_api.ipynb` | RunResult, final answer y salida humana. |
| 5 | `05_lineage_memory_api.ipynb` | Memory / Lineage como auditoria de ejecucion. |
| 6 | `06_integrations_strands_api.ipynb` | Integrations: Strands. |
| 7 | `07_integrations_openai_runtime_api.ipynb` | Integrations: OpenAI Agents framework sobre runtime agnostico. |
| 8 | `08_system_api.ipynb` | System API: registry, skills, agents y pipeline determinista. |
| 9 | `09_graph_api.ipynb` | Graph API: state, nodes, edges y `agent.as_node(...)`. |
| 10 | `10_environment_eval_api.ipynb` | Environment, reward, evals y estadisticas. |
| 11 | `11_multi_agentic_system_api.ipynb` | Sistema multi-agente con agentes deterministas y LM opcional. |
| 12 | `12_multi_agentic_graph_api.ipynb` | Graph multi-agente con nodos, estado y fallback local. |
| 13 | `13_single_agentic_system_api.ipynb` | Recorrido completo single-agent: Tool -> Agent -> Environment -> Eval. |
| 14 | `14_multi_agentic_system_api.ipynb` | Recorrido completo multi-agent: System -> Graph -> Environment -> Eval. |

## Regla De Ejecucion

```python
import agentic_systems as lab

runtime = lab.runtime(provider="auto")
```

Configura credenciales fuera del notebook, antes de abrir Jupyter/VSCode:

```bash
cp .env.example .env
```

```powershell
$env:OPENAI_API_KEY="your_key_here"
$env:AWS_REGION="us-east-1"
$env:AWS_PROFILE="your_profile"
```

En Git Bash usa `export`:

```bash
export OPENAI_API_KEY="your_key_here"
export AWS_REGION="us-east-1"
export AWS_PROFILE="your_profile"
```

Los notebooks no piden ni guardan secretos. Verifica la seleccion efectiva con:

```python
lab.show(lab.runtime(provider="auto").describe(), title="Auto runtime - describe")
```

No hay rutas ocultas de negocio ni dependencias en `examples/`.


