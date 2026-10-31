# Lineage y Memory entre agentes y ejecuciones · 2.1.4.dev7

Ejecutado offline contra el wheel instalado fuera del checkout. Cero inferencia y cero intentos externos.

Input → System → Agent fees calcula comisión → Agent reviewer aplica política → Output.
Memory se adjunta al System: cada ejecución completa produce un episodio; los agentes heredan esa vista.
El revisor exige evidencia actual de fees consistente con la política. Después consulta el linaje estructurado de los episodios: si PAY-001 ya fue aprobado, devuelve review_duplicate.
El mismo input pasa de approve a review_duplicate exclusivamente por Memory. Sin Memory vuelve a approve; sin linaje actual o con fee inconsistente, la ejecución falla.

El estado público contiene únicamente payment_id, amount, fee y decision. Context y episodios se observan aparte; el estado interno conserva referencias acotadas a evidencia.

| Ejecución | Agente | Observaciones previas actuales | Episodios anteriores |
|---|---|---|---|
| 1 | fees | 0 | 0 |
| 1 | reviewer | 1 | 0 |
| 2 | fees | 0 | 1 |
| 2 | reviewer | 1 | 1 |

## Ejecución 1

```text
payments: COMPLETED
Execution: run-6739cb89861343efbe2dbe576a50286e
Input: {"payment_id":"PAY-001","amount":5000}
Output: {"payment_id":"PAY-001","amount":5000,"fee":50,"decision":"approve"}
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
      "execution_id": "run-fc36abae8bf447a1a42d7daef0551d62",
      "name": "fees",
      "ok": true
    }
  ]
}
```

## Ejecución 2

```text
payments: COMPLETED
Execution: run-2e6196794c2d424d8d9cd4a50488a65f
Input: {"payment_id":"PAY-001","amount":5000}
Output: {"payment_id":"PAY-001","amount":5000,"fee":50,"decision":"review_duplicate"}
Process:
- Agent fees: completed
- Tool calculate_fee: completed -> {"fee":50}
- Agent reviewer: completed
- Tool decide: completed -> {"decision":"review_duplicate"}
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
      "execution_id": "run-6739cb89861343efbe2dbe576a50286e",
      "lineage": {
        "answer": "{\"payment_id\": \"PAY-001\", \"amount\": 5000, \"fee\": 50, \"decision\": \"approve\"}",
        "execution_id": "run-6739cb89861343efbe2dbe576a50286e",
        "failed_steps": 0,
        "ok": true,
        "omitted_steps": 0,
        "steps": [
          {
            "evidence": {
              "data": {
                "amount": 5000,
                "decision": "approve",
                "fee": 50,
                "payment_id": "PAY-001"
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-6739cb89861343efbe2dbe576a50286e",
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
            "step_id": "run-df4a1a8ceae74150aa226e3b226a3954",
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
            "step_id": "tool-fb76b8252bf9497d97adbf8aee18fb76",
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
            "step_id": "run-f0615060aa1c4de09269318bbd8fefd0",
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
            "step_id": "tool-fbea3c04b5c943208374966964a07f06",
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
      "execution_id": "run-6739cb89861343efbe2dbe576a50286e",
      "lineage": {
        "answer": "{\"payment_id\": \"PAY-001\", \"amount\": 5000, \"fee\": 50, \"decision\": \"approve\"}",
        "execution_id": "run-6739cb89861343efbe2dbe576a50286e",
        "failed_steps": 0,
        "ok": true,
        "omitted_steps": 0,
        "steps": [
          {
            "evidence": {
              "data": {
                "amount": 5000,
                "decision": "approve",
                "fee": 50,
                "payment_id": "PAY-001"
              },
              "errors": [],
              "ok": true
            },
            "kind": "execution",
            "source": "python-runtime",
            "step_id": "run-6739cb89861343efbe2dbe576a50286e",
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
            "step_id": "run-df4a1a8ceae74150aa226e3b226a3954",
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
            "step_id": "tool-fb76b8252bf9497d97adbf8aee18fb76",
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
            "step_id": "run-f0615060aa1c4de09269318bbd8fefd0",
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
            "step_id": "tool-fbea3c04b5c943208374966964a07f06",
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
        "fee": 50
      },
      "execution_id": "run-4e686922581c4ac78bc3cb6ac0645885",
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
- Memory terminó con dos episodios; los resultados conservaron solo cuatro campos de negocio.
- Mismo pago sin Memory: approve; con Memory del primer run: review_duplicate.
- Sin evidencia actual de fees: error Missing successful fees lineage.
- Fee incorrecto aunque registrado en el linaje: error Fee is inconsistent with lineage or current policy.

## Context frente a linaje

Context incluye data y sources del dominio, lineage del trabajo actual y episodes históricos. El linaje de un Agent o System puede alimentar Context, pero no sustituye necesariamente la política ni las fuentes externas.

## Alcance de la política de duplicados

Demostración acotada: consulta solo los episodios locales retenidos y los pasos disponibles en su resumen. Un episodio ausente o truncado no demuestra que el pago nunca existió. No sustituye un registro persistente de idempotencia ni garantiza exclusión de duplicados concurrentes.

Memoria local en proceso, sin persistencia ni búsqueda semántica. Linaje observado, no razonamiento privado del modelo.

Wheel SHA-256: `f96d9fc165251e798374a1a9ed6b32e99c2704e210925acf6a579b06cd1a4f16`.
