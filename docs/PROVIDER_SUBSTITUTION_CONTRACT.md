# Runtime and Provider Substitution Contract

Status: normative for Checkpoint 1.1.4.

This contract defines the observable guarantees of replacing one canonical
Provider with another. It does not promise identical model behavior, text,
latency, cost, or vendor-specific features.

## Scope

The contract applies to `python-runtime`, `openai-runtime`, `vllm-runtime`, and
`bedrock-runtime` at the Agent execution boundary. A conforming execution is
observed through `RunResult`, not through a Provider SDK response.

`Runtime` selects and configures an execution path. `Provider` is the adapter
that executes that path and normalizes its observable result. Changing either
MUST preserve the base contract below.

## Base Contract

Every canonical Provider MUST preserve:

1. **Normalized result.** Success and representable execution failure return
   `RunResult` through Agent execution.
2. **Stable identity.** `RunResult.engine` names the Provider that actually
   executed, using its canonical identifier.
3. **Tool evidence.** Executed Tools remain ordered and inspectable in
   `tool_events`; successful calls cannot be inferred only from prose.
4. **Structured failure.** A failed result has `ok=False` and at least one
   structured error, failed Tool event, or failed Contract validation.
5. **Contract validation.** Agent finalization applies the same
   `AgentContract` rules independently of Provider.
6. **Portable serialization.** Public result fields and conformance reports are
   JSON-mode serializable.

The Provider MUST preserve requested `mode`, logical Agent/Tool identities,
policy limits that the adapter accepts, and the distinction between answer,
evidence, validation, errors, usage, and adapter metadata.

## Capability Classes

Required capabilities define conformance and therefore have status
`supported`. Optional capabilities describe legitimate operational variation
and have one of these statuses:

- `supported`: available through the current public adapter contract;
- `degraded`: available with a documented semantic or operational limitation;
- `unsupported`: unavailable; callers must not infer or silently emulate it.

The machine-readable source is `provider_profile(...)`. A caller can validate
requirements before execution:

```python
from agentic_systems.providers import provider_profile

profile = provider_profile("python-runtime")
profile.check(["offline_execution"]).raise_if_failed()
profile.check(["native_async"], allow_degraded=False).raise_if_failed()
```

The second check fails because `python-runtime.arun` is an async compatibility
surface over synchronous Tool execution, not native asynchronous execution.

## Capability Matrix

| Capability | python-runtime | openai-runtime | vllm-runtime | bedrock-runtime |
|---|---|---|---|---|
| Base `RunResult` contract | supported | supported | supported | supported |
| Model generation | unsupported | supported | supported | supported |
| Deterministic execution | supported | unsupported | unsupported | unsupported |
| Native async | degraded | supported | supported | degraded |
| Token usage | degraded | supported | degraded | supported |
| Streaming | unsupported | unsupported | unsupported | unsupported |
| Cancellation | unsupported | unsupported | unsupported | unsupported |
| Offline execution | supported | unsupported | unsupported | unsupported |

Profiles are declarations about the adapter surface, not probes of credentials,
network health, endpoint configuration, or model availability.

## Explicit Degradation

A degraded capability MUST be declared in the selected Provider profile with a
reason. `ProviderProfile.check` emits a warning when degradation is accepted and
an error when `allow_degraded=False`. An unsupported or unknown requested
capability always produces an error.

Fallback to another Provider is a separate decision. If fallback occurs, the
result MUST identify the actual Provider. A successful fallback does not prove
that the preferred and actual Providers are semantically equivalent.

## Legitimate Differences

Conformance does not require equality of:

- generated wording, reasoning path, or model quality;
- token counts when a Provider cannot report equivalent metrics;
- latency, price, rate limits, retries, or service availability;
- deterministic repeatability of generated output;
- vendor-native messages, response objects, or metadata;
- unsupported streaming, cancellation, or sampling controls.

Tests compare common invariants and evidence, not byte-for-byte answers. Domain
applications that need stronger equivalence MUST define an `AgentContract`,
expected Tool evidence, and output assertions for that domain.

## Conformance Suite

`evaluate_provider_conformance(...)` applies one observable suite to successful
and failed results. The primary adapter fixtures use controlled transports while
executing the real normalization code. The report includes named checks,
structured issues, and declared degradations.

The suite is a base floor. Passing it does not certify live credentials,
endpoint availability, model quality, or optional capabilities.

## Counterexamples

- Returning a vendor SDK object from one Agent path instead of `RunResult`.
- Reporting `openai-runtime` after execution actually fell back to Bedrock.
- Marking a run successful while required Contract validation failed.
- Mentioning a Tool in generated text without a corresponding Tool event.
- Treating worker-thread delegation as native async.
- Claiming equal token usage or deterministic text across unrelated models.
