# Input → proceso → output · 2.1.4.dev7

Ejecutado en un kernel nuevo con el wheel instalado fuera del checkout. Python determinista y LangGraph, sin inferencia.

| Entrada (centavos) | Comisión | Total | Decisión | Estado | Recompensa del episodio |
| ---: | ---: | ---: | --- | --- | ---: |
| 5000 | 50 | 5050 | approve | approved | 1 |
| 12000 | 120 | 12120 | review | pending_review | 1 |

Proceso: Agent Graph calcula fee → total; Agent revisor aplica Context; System elige approve/review_required; Environment registra cada episodio y calcula reward.

Eval: **2/2 casos aprobados**. Cada caso observó tres episodios previos y escribió en una vista privada; producción permanece con **3 episodios**. Recompensa acumulada del Environment: **2**. Es una métrica explícita de update/state/history, no reward= ni entrenamiento automático.

## system

Salida literal de `RunResult.human_results()`:

```text
payments: COMPLETED
Execution: run-bda096dece7449e299ffd612e6bfab22
Input: {"amount":5000}
Output: {"amount":5000,"fee":50,"total":5050,"decision":"approve","status":"approved"}
Process:
- Agent fee_capability: completed
- Tool calculate_fee: completed -> {"amount":5000,"fee":50}
- Tool calculate_total: completed -> {"amount":5000,"fee":50,"total":5050}
- Agent reviewer: completed
- Tool decide: completed -> {"decision":"approve"}
- Decision review -> "approve"
- Step approve: completed
```

## environment

Salida literal de `RunResult.human_results()`:

```text
daily_payments: COMPLETED
Execution: run-5a636ad73a48400283d2e8b3faa8b4c9
Input: {"records_observed":[{"amount":5000,"expected_status":"approved"},{"amount":12000,"expected_status":"pending_review"}]}
Output: {"outputs":[{"amount":5000,"fee":50,"total":5050,"decision":"approve","status":"approved"},{"amount":12000,"fee":120,"total":12120,"decision":"review","status":"pending_review"}],"summary":{"state":{"processed":2,"reward":1,"total_reward":2},"processed":2,"terminated":true,"truncated":false,"reason":"records_exhausted"}}
Process:
- System payments: completed
- Agent fee_capability: completed
- Tool calculate_fee: completed -> {"amount":5000,"fee":50}
- Tool calculate_total: completed -> {"amount":5000,"fee":50,"total":5050}
- Agent reviewer: completed
- Tool decide: completed -> {"decision":"approve"}
- Decision review -> "approve"
- Step approve: completed
8 operations omitted; inspect lineage for full evidence.
```

## eval

Salida literal de `RunResult.human_results()`:

```text
payment_acceptance: COMPLETED
Execution: run-6c1798a630f64e76b9a717e01d4a3ec3
Input: {"cases_executed":[{"amount":5000},{"amount":12000}]}
Output: {"total":2,"passed":2,"failed":0}
Process:
- System payments: completed
- Agent fee_capability: completed
- Tool calculate_fee: completed -> {"amount":5000,"fee":50}
- Tool calculate_total: completed -> {"amount":5000,"fee":50,"total":5050}
- Agent reviewer: completed
- Tool decide: completed -> {"decision":"approve"}
- Decision review -> "approve"
- Step approve: completed
8 operations omitted; inspect lineage for full evidence.
```

[Notebook ejecutado](agent_system_environment_rewards.ipynb) · [RunResults, memoria y linaje capturados](demonstration.json) · [Informe](REPORT.md).
