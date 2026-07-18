# ADR 0007: Framework and Graph Boundary

Status: accepted

Date: 2026-07-18

## Context

The package described LangGraph, OpenAI Agents-style, and Strands uniformly as
framework facades, but only LangGraph had adapter code and an optional
dependency. OpenAI Agents-style affected configuration and metadata while using
the existing Provider loop. Strands was only an accepted label. Provider names
could also appear in the Framework field, and the short `graph(...)` facade was
easy to confuse with portable internal Graph adapters.

## Decision

1. Agentic Systems owns portable primitives, Contracts, RunResult, evidence,
   Provider selection, and explicit state projection.
2. External Frameworks own native state, compilation, lifecycle, persistence,
   and unsupported native capabilities.
3. Framework profiles classify integrations as `native-adapter`, `style-only`,
   or `declarative-only`.
4. LangGraph is the only implemented external Framework adapter in 1.1.5.
5. OpenAI Agents-style and Strands remain accepted compatibility identities but
   do not claim SDK execution.
6. Execution metadata distinguishes the requested Framework from the adapter
   that actually ran.
7. Internal Environment Graph adapters declare `agentic-systems-native`;
   LangGraph wrappers declare `framework-native`.
8. Full RunResult preservation through Graph state requires an explicit
   `result_key`; answer and trace projections are not equivalent substitutes.

## Consequences

- Existing framework strings remain accepted.
- Existing `framework` metadata remains for compatibility and gains explicit
  `framework_requested` and `framework_adapter` fields.
- Providers no longer identify themselves as Frameworks.
- `Agent.as_node` and `as_async_node` are documented as framework-neutral state
  adapters and can preserve a serialized result through `result_key`.
- LangGraph remains optional and is imported only when native graph primitives
  are requested.
- A future Strands or OpenAI Agents SDK adapter must add actual adapter code,
  optional dependencies, a profile update, and the shared preservation suite.

## Rejected Alternatives

**Treat every accepted label as an adapter.** Rejected because metadata alone
cannot establish SDK execution or ownership.

**Move LangGraph types into core.** Rejected because it would make an optional
framework define the central Graph model and dependency boundary.

**Make every Graph return RunResult.** Rejected because Graph state and Agent
execution results have different ownership and composition semantics.

**Wrap every LangGraph feature.** Rejected because a broad compatibility layer
would be brittle; advanced native behavior remains accessible directly.

## Verification

`tests/integration_conformance/test_framework_boundary.py` verifies profiles,
requested/actual metadata, Graph-kind inspection, optional-dependency-free
portable Graphs, and full RunResult preservation through a LangGraph node.
