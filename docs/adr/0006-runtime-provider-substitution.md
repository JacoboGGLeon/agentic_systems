# ADR 0006: Runtime and Provider Substitution

Status: accepted

Date: 2026-07-18

## Context

Agentic Systems exposes four canonical Provider paths, but selection alone did
not define what substitution preserves. Differences in model generation,
asynchrony, usage reporting, endpoint requirements, and deterministic execution
could be mistaken for equivalent semantics. Degradation was described but not
represented by one inspectable contract.

## Decision

1. Provider substitution is defined at the normalized Agent `RunResult`
   boundary, not at vendor SDK response boundaries.
2. Six capabilities are required: normalized result, stable engine identity,
   Tool evidence, structured failure, Contract validation, and JSON
   serialization.
3. Operational capabilities are optional and explicitly classified as
   `supported`, `degraded`, or `unsupported` per canonical Provider.
4. Every primary adapter exposes the same immutable `ProviderProfile` shape.
5. Requested degraded capabilities warn by default and can be rejected with
   `allow_degraded=False`; unsupported capabilities fail validation.
6. One conformance evaluator checks success and failure results from every
   primary adapter using the same observable rules.
7. Passing the base suite does not imply identical generated output, usage,
   latency, cost, determinism, or vendor-native features.

## Consequences

- Consumers can inspect capability differences before execution.
- Conformance failures and degradation decisions are JSON-serializable.
- `python-runtime` satisfies the same base contract while explicitly stating
  that it does not perform model generation.
- Existing Provider execution signatures and top-level exports remain intact.
- New Provider adapters must declare all required and optional capabilities and
  pass the shared suite before being called substitutable.

## Rejected Alternatives

**Promise output equality.** Rejected because probabilistic models and different
Provider implementations cannot guarantee equivalent wording or reasoning.

**Use feature detection through `hasattr`.** Rejected because accidental method
presence does not define semantic support or degradation.

**Silently emulate every optional feature.** Rejected because sync wrappers,
missing token metrics, and fallback Providers have observable limitations.

**Make live credentials part of conformance.** Rejected because configuration
health and adapter semantics are separate concerns. Controlled transports test
normalization; integration smoke tests may test live services independently.

## Verification

`tests/api/test_provider_conformance.py` runs the shared base evaluator against
python-runtime, openai-runtime, vllm-runtime, and bedrock-runtime and verifies
profile validation, explicit degradation, serialization, and clear failures.
