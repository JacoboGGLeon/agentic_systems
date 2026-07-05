# Pytest Coverage Report

Fecha de corte: 2026-07-05

## Estado Actual Verificado

Esta medicion es real. Viene de una ejecucion local de `pytest` con `coverage.py` usando el virtualenv del proyecto; no es un numero escrito a mano. PyPI tambien fue verificado con `pip index versions agentic-systems`, que reporto `agentic-systems (1.0.0)`.

Comando ejecutado:

```powershell
.\.venv_agentic_systems\Scripts\python.exe -m pytest --cov=agentic_systems --cov-report=term-missing -q
```

Resultado funcional:

```text
304 passed, 0 skipped
```

Resultado de coverage:

```text
TOTAL statements: 5299
TOTAL missing: 0
TOTAL coverage: 100.00%
Required test coverage of 100.0% reached.
```


## Estructura De Tests

La suite quedo organizada por superficie publica bajo `tests/api/`:

```text
tests/api/
  test_runtime.py
  test_scheduler.py
  test_tool.py
  test_skill.py
  test_agent.py
  test_compose_result.py
  test_human_result.py
  test_lineage_memory.py
  test_system.py
  test_graph.py
  test_environment_eval.py
  test_integrations_openai_agents.py
  test_integrations_langgraph.py
  test_integrations_strands.py
  test_cli.py
```

Los archivos `tests/api/test_*.py` son los puntos de entrada legibles por simbolo/API. La carpeta `tests/api/_legacy_modules/` conserva cuerpos historicos migrados para no perder cobertura ni comportamiento mientras se estabiliza la nueva taxonomia. El loader preserva las rutas originales de `tests/test_*.py` para que fixtures y calculos de `Path(__file__).parents[1]` sigan apuntando al repo.

## Alcance Cubierto

| Capa | Estado |
|---|---|
| Core execution: `agents.py`, `system.py`, runtime, scheduler | 100% |
| Contracts/results/output contracts/final answer | 100% |
| Tools, skills, factories, chain, expectations | 100% |
| Providers: python-runtime, openai-runtime, bedrock-runtime, vllm-runtime, base | 100% |
| Bedrock Runtime client con fakes | 100% |
| LangGraph facade e integraciones | 100% |
| Environment y evals | 100% |
| Lineage Memory | 100% |
| Human output plain/Rich/debug/lineage/eval/environment | 100% |
| Notebook utilities y `compose_result` | 100% |
| CLI diagnostics | 100% |

## Criterio De Cierre

El objetivo de coverage queda cerrado cuando este comando pasa sin bajar `fail_under = 100`:

```powershell
.\.venv_agentic_systems\Scripts\python.exe -m pytest --cov=agentic_systems --cov-report=term-missing -q
```

Estado actual: cerrado.
