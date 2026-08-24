# Streaming contract (proposed)

Status: design note for Agentic Systems 3.0. This document does not claim that
the public 2.1 API streams results.

## Goal

Expose provider and framework streaming through one portable event contract,
while preserving `RunResult` as the final, normalized execution result.

The public model is:

```text
provider/framework native stream
        -> adapter normalization
        -> RunEvent sequence
        -> final RunResult
```

`RunResult.text`, `RunResult.final` and `RunResult.normalized()` must never expose
private reasoning. Native evidence remains available only through the explicit
raw-evidence projection.

## Proposed API

```python
for event in agent.stream(input):
    ...

async for event in agent.astream(input):
    ...
```

The terminal event contains the same `RunResult` returned by `run()`/`arun()`.
Systems and environments use the same event schema and add component identity,
stage identity and lineage.

## Event taxonomy

- `run.started`
- `model.text.delta`
- `tool.call.started`
- `tool.call.completed`
- `agent.changed`
- `stage.started`
- `stage.completed`
- `usage.updated`
- `run.completed`
- `run.failed`

Every event carries a monotonic sequence number, run identity, provider,
framework, model and JSON-safe payload. Component/stage identifiers are optional
only when the event originates at agent level.

## Configuration

`.env` is the canonical deployment selector:

```dotenv
AGENTIC_SYSTEMS_STREAM_MODE=off
BEDROCK_STREAM_TRANSPORT=auto
```

`AGENTIC_SYSTEMS_STREAM_MODE` accepts `off`, `events`, `tokens` or `all`.
Provider-specific transport settings choose how events are obtained, not the
public event contract. Explicit SDK arguments override `.env`; `.env` overrides
safe defaults.

For Bedrock, `converse-stream` requires
`bedrock:InvokeModelWithResponseStream`; non-streaming Converse only requires
`bedrock:InvokeModel`. OpenAI-compatible providers use their native streaming
transport. Framework adapters may enrich events but cannot change their public
meaning.

## Provider/framework gate

Each declared provider/framework pair must prove:

1. ordered event delivery and one terminal event;
2. cancellation and timeout propagation;
3. normalized tool-call start/completion events;
4. usage reconciliation with the terminal `RunResult`;
5. no fallback or provider identity drift;
6. no private reasoning in public deltas;
7. sync/async equivalence where both capabilities are declared.

Unsupported streaming must fail early with a structured capability error. It
must not silently degrade to a buffered non-streaming call.
