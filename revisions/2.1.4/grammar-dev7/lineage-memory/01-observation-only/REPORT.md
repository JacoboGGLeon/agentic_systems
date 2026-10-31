# Lineage y Memory entre agentes y ejecuciones · 2.1.4.dev7

Ejecutado offline contra el wheel instalado fuera del checkout. Cero inferencia y cero intentos externos.

Input → System → Agent fees calcula comisión → Agent reviewer aplica política → Output.
Memory se adjunta al System: cada ejecución completa produce un episodio; los agentes heredan esa vista.
La decisión depende de la política y los datos actuales. Este ejemplo demuestra entrega del contexto histórico, no aprendizaje ni cambios de política.

El estado público contiene únicamente amount, fee y decision. Context y episodios se observan aparte; el estado interno conserva referencias acotadas a evidencia.

| Ejecución | Agente | Observaciones previas actuales | Episodios anteriores |
|---|---|---|---|
| 1 | fees | 0 | 0 |
| 1 | reviewer | 1 | 0 |
| 2 | fees | 0 | 1 |
| 2 | reviewer | 1 | 1 |

## Ejecución 1

```text
payments: COMPLETED
Execution: run-1d3aca36659a459b8cfec108792b174a
Input: {"amount":5000}
Output: {"amount":5000,"fee":50,"decision":"approve"}
Process:
- Agent fees: completed
- Tool calculate_fee: completed -> {"fee":50}
- Agent reviewer: completed
- Tool decide: completed -> {"decision":"approve"}
```

### Context exacto recibido por fees

```json
{
  "data": {
    "ceiling": 10000,
    "currency": "MXN",
    "fee_bps": 100
  },
  "sources": [
    "payment-policy-v1"
  ],
  "episodes": [],
  "lineage": []
}
```

### Context exacto recibido por reviewer

```json
{
  "data": {
    "ceiling": 10000,
    "currency": "MXN",
    "fee_bps": 100
  },
  "sources": [
    "payment-policy-v1"
  ],
  "episodes": [],
  "lineage": [
    {
      "data": {
        "fee": 50
      },
      "execution_id": "run-911966da09a24b9b805edb2e71975636",
      "name": "fees",
      "ok": true
    }
  ]
}
```

## Ejecución 2

```text
payments: COMPLETED
Execution: run-d4dd3d463a844c7cba3783f0f90d71bd
Input: {"amount":12000}
Output: {"amount":12000,"fee":120,"decision":"review"}
Process:
- Agent fees: completed
- Tool calculate_fee: completed -> {"fee":120}
- Agent reviewer: completed
- Tool decide: completed -> {"decision":"review"}
```

### Context exacto recibido por fees

```json
{
  "data": {
    "ceiling": 10000,
    "currency": "MXN",
    "fee_bps": 100
  },
  "sources": [
    "payment-policy-v1"
  ],
  "episodes": [
    {
      "context": {
        "episode_ids": [],
        "fingerprint": "2b78cb800cc7bca055249311d20ea1121ffd1004657a1ef7a0c2c58c7d8ddaad",
        "memory_revision": 0,
        "sources": [
          "payment-policy-v1"
        ]
      },
      "execution_id": "run-1d3aca36659a459b8cfec108792b174a",
      "lineage": {
        "answer": "{\"amount\": 5000, \"fee\": 50, \"decision\": \"approve\"}",
        "execution_id": "run-1d3aca36659a459b8cfec108792b174a",
        "failed_steps": 0,
        "ok": true,
        "omitted_steps": 0,
        "steps": [
          {
            "evidence": {
              "data": {
                "amount": 5000,
                "decision": "approve",
                "fee": 50
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-1d3aca36659a459b8cfec108792b174a",
            "summary": "completed",
            "title": "payments",
            "why": "Recorded execution evidence"
          },
          {
            "evidence": {
              "data": {
                "fee": 50
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-37df8b0af7004682a6f147d2de7a4695",
            "summary": "completed",
            "title": "calculate_fee",
            "why": "Recorded execution evidence"
          },
          {
            "evidence": {
              "error": null,
              "ok": true,
              "output": {
                "data": {
                  "fee": 50
                }
              }
            },
            "kind": "tool",
            "source": "calculate_fee",
            "step_id": "tool-e77bf9f030494afc8e10f343ef4a3350",
            "summary": "completed",
            "title": "calculate_fee",
            "why": "Recorded Tool event"
          },
          {
            "evidence": {
              "data": {
                "decision": "approve"
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-d3c157ab7832471587028b735f7ad967",
            "summary": "completed",
            "title": "decide",
            "why": "Recorded execution evidence"
          },
          {
            "evidence": {
              "error": null,
              "ok": true,
              "output": {
                "data": {
                  "decision": "approve"
                }
              }
            },
            "kind": "tool",
            "source": "decide",
            "step_id": "tool-66ae0ec45eea4a31a8a2ca90445ce176",
            "summary": "completed",
            "title": "decide",
            "why": "Recorded Tool event"
          }
        ]
      },
      "ok": true,
      "revision": 1
    }
  ],
  "lineage": []
}
```

### Context exacto recibido por reviewer

```json
{
  "data": {
    "ceiling": 10000,
    "currency": "MXN",
    "fee_bps": 100
  },
  "sources": [
    "payment-policy-v1"
  ],
  "episodes": [
    {
      "context": {
        "episode_ids": [],
        "fingerprint": "2b78cb800cc7bca055249311d20ea1121ffd1004657a1ef7a0c2c58c7d8ddaad",
        "memory_revision": 0,
        "sources": [
          "payment-policy-v1"
        ]
      },
      "execution_id": "run-1d3aca36659a459b8cfec108792b174a",
      "lineage": {
        "answer": "{\"amount\": 5000, \"fee\": 50, \"decision\": \"approve\"}",
        "execution_id": "run-1d3aca36659a459b8cfec108792b174a",
        "failed_steps": 0,
        "ok": true,
        "omitted_steps": 0,
        "steps": [
          {
            "evidence": {
              "data": {
                "amount": 5000,
                "decision": "approve",
                "fee": 50
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-1d3aca36659a459b8cfec108792b174a",
            "summary": "completed",
            "title": "payments",
            "why": "Recorded execution evidence"
          },
          {
            "evidence": {
              "data": {
                "fee": 50
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-37df8b0af7004682a6f147d2de7a4695",
            "summary": "completed",
            "title": "calculate_fee",
            "why": "Recorded execution evidence"
          },
          {
            "evidence": {
              "error": null,
              "ok": true,
              "output": {
                "data": {
                  "fee": 50
                }
              }
            },
            "kind": "tool",
            "source": "calculate_fee",
            "step_id": "tool-e77bf9f030494afc8e10f343ef4a3350",
            "summary": "completed",
            "title": "calculate_fee",
            "why": "Recorded Tool event"
          },
          {
            "evidence": {
              "data": {
                "decision": "approve"
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-d3c157ab7832471587028b735f7ad967",
            "summary": "completed",
            "title": "decide",
            "why": "Recorded execution evidence"
          },
          {
            "evidence": {
              "error": null,
              "ok": true,
              "output": {
                "data": {
                  "decision": "approve"
                }
              }
            },
            "kind": "tool",
            "source": "decide",
            "step_id": "tool-66ae0ec45eea4a31a8a2ca90445ce176",
            "summary": "completed",
            "title": "decide",
            "why": "Recorded Tool event"
          }
        ]
      },
      "ok": true,
      "revision": 1
    }
  ],
  "lineage": [
    {
      "data": {
        "fee": 120
      },
      "execution_id": "run-faf2ef5662164d4496c2282dbfa14223",
      "name": "fees",
      "ok": true
    }
  ]
}
```

## Verificaciones

- compile no ejecutó Tools ni escribió Memory.
- Los dos agentes recibieron la política y su fuente.
- reviewer recibió el linaje de fees en ambas ejecuciones.
- En la primera ejecución ninguno recibió episodios anteriores.
- En la segunda ambos recibieron exactamente el episodio de la primera.
- El primer agente de la segunda ejecución no confundió el linaje anterior con el linaje actual.
- Memory terminó con dos episodios; los resultados conservaron solo tres campos de negocio.

Memoria local en proceso, sin persistencia ni búsqueda semántica. Linaje observado, no razonamiento privado del modelo.

Wheel SHA-256: `f96d9fc165251e798374a1a9ed6b32e99c2704e210925acf6a579b06cd1a4f16`.
