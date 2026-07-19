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
| 0.4 | `00_runtime_vllm_provider_api.ipynb` | `vllm-runtime`: provider OpenAI-compatible para Colab/local GPU. |
| 0.5 | `00_runtime_scheduler_api.ipynb` | Scheduler, budgets, retries y timeout. |
| 1 | `01_tool_api.ipynb` | Tool API e IO estructurado. |
| 2 | `02_skill_api.ipynb` | Skill API: tools, prompts, contracts, policy y metadata. |
| 3 | `03_agent_api.ipynb` | Agent API: contexto transformado en acciones. |
| 4 | `04_human_result_api.ipynb` | RunResult, final answer y salida humana. |
| 5 | `05_lineage_memory_api.ipynb` | Memory / Lineage como auditoria de ejecucion. |
| 6 | `06_integrations_strands_api.ipynb` | Strands como identidad `declarative-only`; no SDK adapter. |
| 7 | `07_integrations_openai_runtime_api.ipynb` | OpenAI Agents-style como identidad `style-only`; no Agents SDK adapter. |
| 8 | `08_system_api.ipynb` | Fundamentos de `AgenticSystem`: ownership, registro, Skills, Agents e inspeccion. |
| 9 | `09_graph_api.ipynb` | Fundamentos de Graph: estado, nodos, edges y frontera con LangGraph. |
| 10 | `10_environment_eval_api.ipynb` | Episodios, Environment, seeds, reproducibilidad y Evals. |
| 11 | `11_single_agentic_system_api.ipynb` | Integracion end-to-end de un System con un Agent obligatorio y un explainer LM opcional. |
| 12 | `12_multi_agentic_system_api.ipynb` | Integracion end-to-end de solver, judge y reviewer LM opcional en un solo System. |
| 13 | `13_multi_agentic_graph_api.ipynb` | El sistema multiagente anterior orquestado como Graph con estado, nodos y edges. |

## Regla De Ejecucion

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="auto")
```

Configura credenciales fuera del notebook, antes de abrir Jupyter/VSCode:

```bash
cp .env.example .env
```

```powershell
$env:OPENAI_API_KEY="your_key_here"
$env:AWS_REGION="us-east-1"
$env:AWS_PROFILE="your_profile"
$env:VLLM_BASE_URL="http://127.0.0.1:8000/v1"
$env:VLLM_MODEL="Qwen/Qwen3-0.6B"
```

En Git Bash usa `export`:

```bash
export OPENAI_API_KEY="your_key_here"
export AWS_REGION="us-east-1"
export AWS_PROFILE="your_profile"
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_MODEL="Qwen/Qwen3-0.6B"
```

Los notebooks no piden ni guardan secretos. Verifica la seleccion efectiva con:

```python
toolkit.show(toolkit.runtime(provider="auto").describe(), title="Auto runtime - describe")
```

No hay rutas ocultas de negocio ni dependencias en `examples/`.



## Alias publico

Los notebooks usan `toolkit` como alias de `agentic_systems` para subrayar que se consume la fachada publica de la libreria, no modulos internos.

## Contrato De Release Candidate

Los 18 notebooks deben:

- importar solo `agentic_systems as toolkit`;
- iniciar sin outputs persistidos;
- compilar todas sus celdas de codigo;
- registrar skips de Providers opcionales sin presentarlos como ejecucion;
- separar Provider ejecutable de identidad Framework.

La suite automatica verifica estructura y compilacion. La ejecucion completa
desde kernels limpios es el gate manual posterior descrito en
`docs/RELEASE_CANDIDATE_1_1.md`.
