# Ejecución demostrativa · 2.1.4.dev6

Python determinista y LangGraph, desde el wheel instalado fuera del checkout. Sin inferencia.

Input: 5000 centavos. Proceso: validar, calcular 1% de comisión, revisar total y decidir.
Output: 50 centavos de comisión y pago aprobado.

## agent_graph

RunResult: `{"ok": true, "status": "completed", "execution_id": "run-16da57de7f1e4b04988c5ddb9b3b0a6e", "data": {"amount": 5000, "fee": 50}}`

Salida literal de `result.human_results(max_steps=12, max_chars=5000)`:

```text
fee_capability: COMPLETED
Execution: run-16da57de7f1e4b04988c5ddb9b3b0a6e
Input: not recorded
Output: {"amount":5000,"fee":50}
Process (recorded steps):
- {"name":"fee_capability","status":"completed","id":"run-16da57de7f1e4b04988c5ddb9b3b0a6e"}
- {"name":"tool","status":"completed","id":"run-75c6b27f2e74441eba7d8a8a0958ce46"}
- {"name":"validate","status":"completed","id":"tool-33a11cff9f164dbfb8edb557260fcd6c"}
- {"name":"tool","status":"completed","id":"run-b548180fcaaf401c98a75d6638a03af4"}
- {"name":"calculate_fee","status":"completed","id":"tool-90059ffd4094435c9d67f263fe3960be"}
```

## agent_reviewer

RunResult: `{"ok": true, "status": "completed", "execution_id": "run-299c157f66a8496d8cec1d1ab617cc0a", "data": {"decision": "approve"}}`

Salida literal de `result.human_results(max_steps=12, max_chars=5000)`:

```text
reviewer: COMPLETED
Execution: run-299c157f66a8496d8cec1d1ab617cc0a
Input: not recorded
Output: {"decision":"approve"}
Process (recorded steps):
- {"name":"reviewer","status":"decide -> {\"decision\": \"approve\"}","id":"run-299c157f66a8496d8cec1d1ab617cc0a"}
- {"name":"reviewer","status":"decide -> {\"decision\": \"approve\"}","id":"run-00198527f64b4d2aaf15a2a0ebd320cf"}
- {"name":"eval","status":"decide -> {\"decision\": \"approve\"}","id":"run-5c5d951695934e45b9e097b7e8d0551c"}
- {"name":"decide","status":"completed","id":"tool-d1973496828345fda569646c221b7b7a"}
```

## system

RunResult: `{"ok": true, "status": "completed", "execution_id": "run-a3173c85473044c6bf8eb07a4c366825", "data": {"amount": 5000, "fee": 50, "decision": "approve", "status": "approved"}}`

Salida literal de `result.human_results(max_steps=12, max_chars=5000)`:

```text
payments: COMPLETED
Execution: run-a3173c85473044c6bf8eb07a4c366825
Input: {"amount":5000}
Output: {"amount":5000,"fee":50,"decision":"approve","status":"approved"}
Process (recorded steps):
- {"name":"payments","status":"completed","id":"run-a3173c85473044c6bf8eb07a4c366825"}
- {"name":"tool","status":"completed","id":"run-75c6b27f2e74441eba7d8a8a0958ce46"}
- {"name":"validate","status":"completed","id":"tool-33a11cff9f164dbfb8edb557260fcd6c"}
- {"name":"tool","status":"completed","id":"run-b548180fcaaf401c98a75d6638a03af4"}
- {"name":"calculate_fee","status":"completed","id":"tool-90059ffd4094435c9d67f263fe3960be"}
- {"name":"Next node","status":"approve","id":"run-979cb9b50bab4d5e8201aaa01d0eddee:decision"}
- {"name":"reviewer","status":"decide -> {\"decision\": \"approve\"}","id":"run-00198527f64b4d2aaf15a2a0ebd320cf"}
- {"name":"eval","status":"decide -> {\"decision\": \"approve\"}","id":"run-5c5d951695934e45b9e097b7e8d0551c"}
- {"name":"decide","status":"completed","id":"tool-d1973496828345fda569646c221b7b7a"}
- {"name":"approve","status":"completed","id":"run-89c43cad06ec45be969e6b5bae00e152"}
```

## environment

RunResult: `{"ok": true, "status": "completed", "execution_id": "run-4db521970ec249409e09d3882d174caa", "data": {"outputs": [{"amount": 5000, "fee": 50, "decision": "approve", "status": "approved"}, {"amount": 12000, "fee": 120, "decision": "review", "status": "pending_review"}], "history": [{"step": 0, "record": {"amount": 5000}, "state_before": {}, "state_after": {"processed": 1}, "execution_id": "run-29a0bb90301243b0b2eaa29f31c75610"}, {"step": 1, "record": {"amount": 12000}, "state_before": {"processed": 1}, "state_after": {"processed": 2}, "execution_id": "run-ac55a7d09993475a832b6ee0c0f0fca1"}], "summary": {"state": {"processed": 2}, "processed": 2, "terminated": true, "truncated": false, "reason": "records_exhausted"}}}`

Salida literal de `result.human_results(max_steps=12, max_chars=5000)`:

```text
daily_payments: COMPLETED
Execution: run-4db521970ec249409e09d3882d174caa
Input: {}
Output: {"outputs":[{"amount":5000,"fee":50,"decision":"approve","status":"approved"},{"amount":12000,"fee":120,"decision":"review","status":"pending_review"}],"history":[{"step":0,"record":{"amount":5000},"state_before":{},"state_after":{"processed":1},"execution_id":"run-29a0bb90301243b0b2eaa29f31c75610"},{"step":1,"record":{"amount":12000},"state_before":{"processed":1},"state_after":{"processed":2},"execution_id":"run-ac55a7d09993475a832b6ee0c0f0fca1"}],"summary":{"state":{"processed":2},"processed":2,"terminated":true,"truncated":false,"reason":"records_exhausted"}}
Process (recorded steps):
- {"name":"daily_payments","status":"completed","id":"run-4db521970ec249409e09d3882d174caa"}
- {"name":"observe","status":"completed","id":"run-f014e32944b0489ebe81bc03d545fefd"}
- {"name":"Next node","status":"run","id":"run-f014e32944b0489ebe81bc03d545fefd:decision"}
- {"name":"tool","status":"completed","id":"run-facbbfb43c8d4c7a806d14169a13926b"}
- {"name":"validate","status":"completed","id":"tool-6955d6f851684d6ea6a335654969831b"}
- {"name":"tool","status":"completed","id":"run-64c3d3056c604cf7895bdbecf5991190"}
- {"name":"calculate_fee","status":"completed","id":"tool-1fb31fe547ce4552ab4d91745410251c"}
- {"name":"Next node","status":"approve","id":"run-891aed4233a945c99f917c95b79fe874:decision"}
- {"name":"reviewer","status":"decide -> {\"decision\": \"approve\"}","id":"run-8d895a381a114ef984b6742e51afa8a3"}
- {"name":"eval","status":"decide -> {\"decision\": \"approve\"}","id":"run-88e0ae3f8c744fa7bc329e51b55fcaa7"}
- {"name":"decide","status":"completed","id":"tool-53a33576881e4d7b8298a497f83e2c4e"}
- {"name":"approve","status":"completed","id":"run-cf677489ea8b4596959be05f90f49017"}
17 steps omitted; inspect lineage by execution ID.
```

## eval

RunResult: `{"ok": true, "status": "completed", "execution_id": "run-77fee5cde86c4f6c9c26f9157c57af3b", "data": {"total": 1, "passed": 1, "failed": 0, "cases": [{"name": "0", "ok": true, "input": {"amount": 5000}, "execution_id": "run-9384f235bcc843e4b29599176284d015", "checks": [{"ok": true, "path": "ok"}, {"ok": true}], "judge": null}]}}`

Salida literal de `result.human_results(max_steps=12, max_chars=5000)`:

```text
fee_acceptance: COMPLETED
Execution: run-77fee5cde86c4f6c9c26f9157c57af3b
Input: {}
Output: {"total":1,"passed":1,"failed":0,"cases":[{"name":"0","ok":true,"input":{"amount":5000},"execution_id":"run-9384f235bcc843e4b29599176284d015","checks":[{"ok":true,"path":"ok"},{"ok":true}],"judge":null}]}
Process (recorded steps):
- {"name":"fee_acceptance","status":"completed","id":"run-77fee5cde86c4f6c9c26f9157c57af3b"}
- {"name":"Next node","status":"__end__","id":"run-b4f9e62f1d7f4c97af0e251ec604b7b7:decision"}
- {"name":"tool","status":"completed","id":"run-fa2eccfe655b4f339ee6bc390199cd16"}
- {"name":"validate","status":"completed","id":"tool-493a3bec554945a08b23d9e11367d2bb"}
- {"name":"tool","status":"completed","id":"run-1961c061d2d047889a3091212c612203"}
- {"name":"calculate_fee","status":"completed","id":"tool-ec0eaa8a7a9a485fad52e25e25d62afe"}
- {"name":"Next node","status":"approve","id":"run-6ecd003567a34b7bbcc8cf0e6f4d5eaf:decision"}
- {"name":"reviewer","status":"decide -> {\"decision\": \"approve\"}","id":"run-ba1dbcd2ee2a474bb2bc7b29ff6e8c19"}
- {"name":"eval","status":"decide -> {\"decision\": \"approve\"}","id":"run-70803abd64c548db9e32a7cdfca5e8b5"}
- {"name":"decide","status":"completed","id":"tool-21191b3366fd4c9ab82cb050615ecd76"}
- {"name":"approve","status":"completed","id":"run-7eb8862b0cf34f478fc6232af99f90f0"}
```

Memory: 0 → 1 → 3 → 4 episodios. Los casos de Eval también ejecutan el System y escriben Memory.

Los resultados de ambos Agents se extraen del RunResult del System: no son ejecuciones inventadas ni repeticiones.

[Evidencia completa](run-results.json). Cero solicitudes de inferencia; todos los invariantes aprobados.

## Context y Memory observados

```json
[
  {
    "execution": "system",
    "system_id": "run-a3173c85473044c6bf8eb07a4c366825",
    "sources": [
      "payment-policy-v1"
    ],
    "memory_revision": 0,
    "previous_episodes": 0
  },
  {
    "execution": "environment",
    "system_id": "run-0af7b53848a24cf8a081bba812f4cb6d",
    "sources": [
      "payment-policy-v1"
    ],
    "memory_revision": 1,
    "previous_episodes": 1
  },
  {
    "execution": "environment",
    "system_id": "run-6344c47c126b4257a28cb7ee453edd72",
    "sources": [
      "payment-policy-v1"
    ],
    "memory_revision": 2,
    "previous_episodes": 2
  },
  {
    "execution": "eval",
    "system_id": "run-9384f235bcc843e4b29599176284d015",
    "sources": [
      "payment-policy-v1"
    ],
    "memory_revision": 3,
    "previous_episodes": 3
  }
]
```

## Detalle de presentación detectado

El Agent anidado imprime `Input: not recorded`; sus eventos de Tools sí
conservan la entrada original. No se modificó ni rellenó la vista del SDK.

```json
[
  {
    "name": "validate",
    "input": {
      "amount": 5000
    },
    "output": {
      "data": {
        "amount": 5000
      }
    },
    "ok": true
  },
  {
    "name": "calculate_fee",
    "input": {
      "amount": 5000
    },
    "output": {
      "data": {
        "fee": 50
      }
    },
    "ok": true
  }
]
```
