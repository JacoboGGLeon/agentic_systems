# Pytest Coverage Report

Fecha de corte: 2026-07-01

## Estado Actual

Comando de medicion:

```powershell
.\.venv_agentic_systems\Scripts\python.exe -m pytest `
  --basetemp=C:\Users\jacob\Documents\agentic_systems_pytest_tmp `
  --cache-clear `
  --cov=agentic_systems `
  --cov-report=term-missing `
  --cov-report=json:C:\Users\jacob\Documents\agentic_systems_coverage.json `
  -q
```

Resultado funcional:

```text
264 passed, 1 skipped
```

Resultado de coverage:

```text
coverage: 96.11%
display: 96%
statements: 5137
covered lines: 4937
missing lines: 200
fail_under: 100
```

La suite funcional esta verde. El fallo actual es exclusivamente el umbral de coverage configurado en `pyproject.toml`.

## Fase 0 - Alcance De Coverage

El objetivo no es maquillar coverage. El objetivo es que `100%` signifique cobertura de la API productiva de Agentic Systems.

### Cobertura Contractual Obligatoria

| Capa | Archivos/API | Estado |
|---|---|---|
| Core execution | `agents.py`, `system.py`, `core/runtime.py`, `core/scheduler.py` | Required |
| Contracts and results | `contracts.py`, `results.py`, `final_answer.py`, `output_contracts.py` | Required |
| Tools and skills | `tools/*`, `skills/*` | Required |
| Providers with fakes | `providers/python_direct.py`, `providers/openai_runtime.py`, `providers/base.py` | Required |
| Environment and evals | `environments.py`, `evals.py` | Required |
| Lineage core | `lineage.py` public constructors, serialization and prompt context | Required |
| CLI diagnostics | `cli.py` doctor/runtime paths | Required |

### Cobertura Opcional O Condicional

Estas rutas no se eliminan del plan. Se cubren con fakes cuando representen contrato publico. Solo se excluyen ramas que dependan de infraestructura externa, SDK opcional o rendering no determinista.

| Capa | Archivos/API | Criterio |
|---|---|---|
| Live Bedrock client | `bedrock_runtime_client.py`, `providers/bedrock_runtime.py` | Unit tests use fakes; live AWS smoke belongs outside unit coverage. |
| Optional framework adapters | `integrations/langgraph.py` dependency/version branches | Cover facade behavior with fake modules; exclude only truly external defensive branches. |
| Human rendering variants | `human_output.py` rich/visual formatting branches | Cover public plain output; mark purely visual fallbacks explicitly if kept. |
| Notebook utilities | `utils.py` environment repair/display helpers | Cover deterministic helpers; exclude local-machine repair branches if needed. |

## Principales Huecos Actuales

| Archivo | Statements | Missing | Coverage |
|---|---:|---:|---:|
| `src\agentic_systems\human_output.py` | 568 | 84 | 85% |
| `src\agentic_systems\utils.py` | 633 | 17 | 97% |
| `src\agentic_systems\bedrock_runtime_client.py` | 97 | 75 | 23% |
| `src\agentic_systems\providers\bedrock_runtime.py` | 12 | 12 | 0% |
| `src\agentic_systems\engines\names.py` | 20 | 3 | 85% |
| `src\agentic_systems\system.py` | 219 | 5 | 98% |
| `src\agentic_systems\agents.py` | 274 | 2 | 99% |
| `src\agentic_systems\contracts.py` | 195 | 2 | 99% |

## Decisiones De Implementacion

1. No bajar `fail_under = 100`.
2. No excluir archivos completos hasta demostrar que son live-only u opcionales.
3. Agregar tests primero sobre providers, core, environment/evals y results.
4. Para Bedrock live, usar fakes/mocks en unit tests y dejar smoke live fuera de coverage obligatorio.
5. Para LangGraph, usar modulo fake para cubrir la fachada sin requerir versiones externas concretas.
6. Para OpenAI, usar fake sync/async client; nunca llamar API real en unit tests.
7. Para human output, cubrir API publica estable y marcar ramas visuales/dependientes de Rich solo si son puramente cosmeticas.
8. Toda exclusion nueva debe tener comentario `pragma: no cover` o entrada `omit` justificada en este documento.

## Criterio De Cierre

El trabajo de coverage termina cuando estos comandos pasan:

```powershell
.\.venv_agentic_systems\Scripts\python.exe -m pytest `
  --basetemp=C:\Users\jacob\Documents\agentic_systems_pytest_tmp `
  --cache-clear `
  -q

.\.venv_agentic_systems\Scripts\python.exe -m pytest `
  --basetemp=C:\Users\jacob\Documents\agentic_systems_pytest_tmp `
  --cache-clear `
  --cov=agentic_systems `
  --cov-report=term-missing `
  -q
```

Esperado final:

```text
100% coverage
0 failures por coverage
```


## Fase 1 - Providers

Estado: completada.

Cambios implementados:

- Agregado `tests/test_providers_phase1_coverage.py`.
- Cubierto `providers/__init__.py` al 100%.
- Cubierto `providers/base.py` al 100%.
- Cubierto `providers/openai_runtime.py` al 100% con fake sync/async clients.
- Cubierto `providers/python_direct.py` al 100% con planes, pipelines, errores y async path.
- Corregido bug real en `_tool_choice`: valores no-string ya no generan `TypeError`; caen a `"auto"`.

Resultado despues de fase 1:

```text
228 passed, 1 skipped
coverage: 74.98%
```

Providers despues de fase 1:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/providers/__init__.py` | 100% | cerrado |
| `src/agentic_systems/providers/base.py` | 100% | cerrado |
| `src/agentic_systems/providers/openai_runtime.py` | 100% | cerrado |
| `src/agentic_systems/providers/python_direct.py` | 100% | cerrado |
| `src/agentic_systems/providers/mock.py` | 100% | cerrado |
| `src/agentic_systems/providers/bedrock_runtime.py` | 0% | pendiente: live/compat wrapper |

Nota: `providers/bedrock_runtime.py` no se cubrio en fase 1 porque es una ruta live/compat pequena. Se debe decidir si se cubre con fake import o se omite justificadamente junto con Bedrock live.


## Fase 2 - Core Execution

Estado: completada.

Cambios implementados:

- Agregado `tests/test_core_phase2_coverage.py`.
- Cubierto `core/runtime.py` al 100%.
- Cubierto `core/scheduler.py` al 100%.
- Subido `agents.py` a 99%.
- Subido `contracts.py` a 99%.
- Subido `system.py` a 98%.
- Cubiertos paths sync/async de scheduler, retries, timeouts, backoff, runtime `.env`, `provider="auto"`, async fallback de Agent, scheduler failures y validacion de contratos.

Resultado despues de fase 2:

```text
233 passed, 1 skipped
coverage: 76.85%
```

Core despues de fase 2:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/core/runtime.py` | 100% | cerrado |
| `src/agentic_systems/core/scheduler.py` | 100% | cerrado |
| `src/agentic_systems/agents.py` | 99% | casi cerrado; 2 lineas residuales |
| `src/agentic_systems/contracts.py` | 99% | casi cerrado; 2 lineas residuales |
| `src/agentic_systems/system.py` | 98% | casi cerrado; 5 lineas residuales |

Residuales core actuales:

- `agents.py`: lineas 45, 516.
- `contracts.py`: lineas 153, 239.
- `system.py`: lineas 256, 488-489, 496-497.

Nota: las lineas residuales son ramas defensivas o paths de import opcional. Se pueden cerrar en una fase de residuos o justificar con `pragma: no cover` si se confirma que no representan contrato productivo.

## Fase 3 - Environment/Evals

Estado: completada.

Cambios implementados:

- Agregado `tests/test_environment_eval_phase3_coverage.py`.
- Cubierto `environments.py` al 100%.
- Cubierto `evals.py` al 100%.
- Corregido bug real en `run_eval`: `environment_kwargs={"name": ...}` ya no duplica `name` al construir `AgenticEnvironment`.
- Eliminada una rama defensiva inalcanzable en `_case_actual_summary`; `data` y `final` ya se normalizan antes del loop.
- Cubiertos `AgentStepGraph`, `DynamicAgentRouterGraph`, `PlannedAgentGraph`, `transition_fn`, `reward_fn`, `memory_updater`, `observation_mapper`, normalized output, lineage y `Evaluator` facade.

Resultado despues de fase 3:

```text
236 passed, 1 skipped
coverage: 78.83%
```

Environment/Evals despues de fase 3:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/environments.py` | 100% | cerrado |
| `src/agentic_systems/evals.py` | 100% | cerrado |

## Fase 4 - Results, Final Answer, Output Contracts Y Lineage

Estado: completada.

Cambios implementados:

- Agregado `tests/test_results_lineage_phase4_coverage.py`.
- Cubierto `results.py` al 100%.
- Cubierto `final_answer.py` al 100%.
- Cubierto `output_contracts.py` al 100%.
- Cubierto `lineage.py` al 100%.
- Cubiertas ramas de normalizacion de `RunResult`, `ToolEvent`, `OutputSchema`, `AgenticOutput.compact_dict`, `LineageMemory.from_run_result`, render humano, prompt context, evidencia portable y helpers defensivos.
- Sin cambios de API productiva en esta fase; los ajustes fueron tests y cobertura de contratos existentes.

Resultado despues de fase 4:

```text
245 passed, 1 skipped
coverage: 83.19%
```

Results/Lineage despues de fase 4:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/results.py` | 100% | cerrado |
| `src/agentic_systems/final_answer.py` | 100% | cerrado |
| `src/agentic_systems/output_contracts.py` | 100% | cerrado |
| `src/agentic_systems/lineage.py` | 100% | cerrado |

## Fase 5 - Tools, Skills, Factories, Chain Y Expectations

Estado: completada.

Cambios implementados:

- Agregado `tests/test_tools_skills_factories_phase5_coverage.py`.
- Cubierto `tools/tool.py` al 100%.
- Cubierto `skills/skill.py` al 100%.
- Cubierto `skills/loader.py` al 100%.
- Cubierto `factories.py` al 100%.
- Cubierto `chain.py` al 100%.
- Cubierto `expectations.py` al 100%.
- Corregido bug real en `factories.load_skill`: una `Skill` valida pero sin tools ya no se pierde por ser falsy via `__len__`.
- Cubiertos contratos de Tool, Skill, loader de filesystem, factories canonicas, Chain y expectations sin llamadas live.

Resultado despues de fase 5:

```text
250 passed, 1 skipped
coverage: 85.16%
```

Tools/Skills/Factories despues de fase 5:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/tools/tool.py` | 100% | cerrado |
| `src/agentic_systems/skills/skill.py` | 100% | cerrado |
| `src/agentic_systems/skills/loader.py` | 100% | cerrado |
| `src/agentic_systems/factories.py` | 100% | cerrado |
| `src/agentic_systems/chain.py` | 100% | cerrado |
| `src/agentic_systems/expectations.py` | 100% | cerrado |

## Fase 6a - CLI Y LangGraph Integration

Estado: completada.

Cambios implementados:

- Agregado `tests/test_cli_langgraph_phase6_coverage.py`.
- Cubierto `cli.py` al 100%.
- Cubierto `integrations/langgraph.py` al 100% con modulos fake de LangGraph.
- Eliminada una rama inalcanzable en `_answer_from_payload`: el fallback de resumen publico ya ocurria dentro de la llamada recursiva.
- Cubiertos `doctor`, `runtime`, `public-api`, `api`, helpers de nodos, `GraphApp`, `AgenticGraph`, builders de agent graph/planned graph y projection de Lineage Memory desde estados LangGraph.

Resultado despues de fase 6a:

```text
256 passed, 1 skipped
coverage: 89.47%
```

CLI/LangGraph despues de fase 6a:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/cli.py` | 100% | cerrado |
| `src/agentic_systems/integrations/langgraph.py` | 100% | cerrado |
| `src/agentic_systems/human_output.py` | 54% | pendiente fase 6b |
| `src/agentic_systems/utils.py` | 72% | pendiente fase 6b |



## Fase 6b - Human Output Y Utils

Estado: completada.

Cambios implementados:

- Agregado `tests/test_human_output_utils_phase6b_coverage.py`.
- Cubiertos caminos deterministas de `human_output.py`: rendering plain, `debug`, eval/environment blocks, SQL/table blocks, validacion, lineage explicito, wrappers `human_result`/`human_results` y helpers de normalizacion.
- Cubiertos caminos deterministas de `utils.py`: `agent_output`, compare helpers, trace compaction, summaries de run/environment/eval, masking, show de objetos con `human_text`, parsing de answers, JSON bounded summaries, coercion de campos y discovery de repo.
- No se tocaron llamadas live de OpenAI/Bedrock ni se bajo `fail_under`.
- Se uso `codebase-memory-mcp` para confirmar firmas reales de helpers antes de ajustar expectativas de tests.

Resultado despues de fase 6b:

```text
264 passed, 1 skipped
coverage: 96.11%
```

Human Output/Utils despues de fase 6b:

| Archivo | Coverage | Estado |
|---|---:|---|
| `src/agentic_systems/human_output.py` | 85.21% | pendiente: ramas Rich/visuales y defensivas finales |
| `src/agentic_systems/utils.py` | 97.31% | casi cerrado; 17 lineas residuales |

Residuales principales despues de fase 6b:

| Archivo | Coverage | Residual |
|---|---:|---|
| `src/agentic_systems/bedrock_runtime_client.py` | 22.68% | cliente live Bedrock; requiere fakes o exclusion justificada |
| `src/agentic_systems/providers/bedrock_runtime.py` | 0.00% | wrapper live Bedrock; requiere fake import o exclusion justificada |
| `src/agentic_systems/human_output.py` | 85.21% | ramas Rich/pretty, fallback de lineage por excepcion y validaciones cosmeticas |
| `src/agentic_systems/utils.py` | 97.31% | ramas defensivas de parsing, trace y mapper invalido |
| `src/agentic_systems/engines/names.py` | 85.00% | alias/error paths residuales |
| `src/agentic_systems/system.py` | 97.72% | ramas defensivas finales |
| `src/agentic_systems/agents.py` | 99.27% | 2 lineas residuales |
| `src/agentic_systems/contracts.py` | 98.97% | 2 lineas residuales |

## Siguiente Fase

Fase 7: cerrar residuales para llegar a `100%` real. Prioridad:

1. `bedrock_runtime_client.py` y `providers/bedrock_runtime.py` con cliente fake, sin AWS live.
2. Remates de `human_output.py` Rich/pretty y defensivos.
3. Remates pequenos de `utils.py`, `agents.py`, `contracts.py`, `system.py` y `engines/names.py`.
4. Decidir si alguna rama live-only merece `pragma: no cover` con justificacion documentada.
