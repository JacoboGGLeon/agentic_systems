# Migration Guide: Agentic Systems 1.0 to 1.1

Status: stable guidance for upgrading 1.0 applications to the current 1.1 line.

## Scope

Agentic Systems 1.1 preserves the top-level import:

```python
import agentic_systems as toolkit
```

The 1.1 work formalizes contracts that were implicit in 1.0. It does not add an
algebraic syntax layer or promise identical behavior across model Providers.

## Upgrade

```bash
python -m pip install "agentic-systems==1.1.2"
```


## Runtime And Provider

Use canonical Provider names:

```python
runtime = toolkit.runtime(provider="python-runtime")
runtime = toolkit.runtime(provider="auto")
```

`python-direct` remains a compatibility alias, but new code and tutorials use
`python-runtime`. Provider substitution preserves the common RunResult contract,
not identical model output, latency, usage accounting, streaming, or tool-choice
behavior.

Inspect static Provider declarations before execution:

```python
profiles = [
    profile.to_dict()
    for profile in toolkit.providers.provider_profiles()
]
```

`provider="auto"` is observable and may remain unresolved. It is not evidence
that credentials, endpoints, or a model are available.

## Frameworks And Graphs

Only LangGraph has an external Framework adapter in 1.1.

| Identity | 1.1 meaning |
|---|---|
| `langgraph` | Implemented optional adapter |
| `openai-agents` | Style-only metadata; no OpenAI Agents SDK adapter |
| `strands` | Declarative-only metadata; no Strands SDK adapter |

Provider selection and Framework identity are separate. A Framework label does
not prove that an external SDK executed.

## RunResult

Tool and Agent execution still returns `RunResult`. Consumers should use stable
fields instead of inferring success from text alone:

```python
result.ok
result.final
result.data
result.text
result.tool_events
result.usage
result.validation
result.errors
```

1.1 validates contradictions between success, validation, errors, partial
failure, and evidence more explicitly. Serialize through `to_dict()` or existing
normalized projections rather than serializing arbitrary executable objects.

## Tool And Skill Composition

Different Tool or Skill definitions with the same identity no longer compose
ambiguously. The default is an error. Use `on_conflict="keep"` or
`on_conflict="replace"` only when precedence is intentional, and inspect
composition history after an override.

A Skill remains a package of Tools, prompts, contracts, policy, assets, and
metadata. It is not an autonomous Agent.

## Systems And Static Inspection

`AgenticSystem.inspect()` remains dictionary-compatible and returns public
`InspectReport`:

```python
inspection = system.inspect()
inspection.raise_if_errors()
structured = inspection.to_dict()
human = inspection.human_text()
```

Inspection reports entities, relationships, contracts, Providers, Frameworks,
capabilities, conflicts, limits, and degradation risks. It does not execute
models or Tools and does not certify live infrastructure.

## Environments And Evals

System composition, Graph transition state, Environment episode state, and Eval
verification state have separate owners. Reproducibility must be classified:

```python
report = toolkit.run_eval(
    agent,
    cases,
    determinism="deterministic",
    seed=17,
    reproducibility_conditions=[
        "same local fixtures",
        "python-runtime",
        "same Agent contract and policy",
    ],
)
```

Use `seeded` only when replay depends on a seed and `non_deterministic` when
behavior cannot be reproduced under stated conditions.

## Execution Context

Do not import or construct `ExecutionContext`. In 1.1 it remains a conceptual
resolution view. Existing owners remain authoritative:

- Runtime and Provider: `RuntimeConfig`;
- composition: `AgenticSystem`;
- per-run behavior: `RunPolicy`;
- state: Graph and Environment;
- correlation and evidence: `RunResult`.

## Migration Checklist

1. Replace taught `python-direct` usage with `python-runtime`.
2. Separate `provider` from `framework`.
3. Remove claims that Strands or OpenAI Agents SDK adapters execute.
4. Resolve Tool and Skill collisions explicitly.
5. Read RunResult evidence and validation fields directly.
6. Classify Eval reproducibility and record replay conditions.
7. Add `system.inspect()` as a pre-execution gate.
8. Run the full test suite and notebooks required by your deployment.
