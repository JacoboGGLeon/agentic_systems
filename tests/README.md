# Test Matrix

The suite is organized by the contract owner, not by migration history.

| Area | Responsibility |
|---|---|
| `tests/api/` | Public behavior for Runtime, Tool, Skill, Agent, System, Graph, Environment, Eval, results and output. |
| `tests/unit/` | Private branches owned by individual production modules. |
| `tests/providers/` | Provider base, OpenAI, Python Runtime, vLLM and Bedrock behavior with fake clients. |
| `tests/contracts/` | Public inventory, semantic invariants, optional-import boundary and frozen Bedrock signatures. |
| `tests/frameworks/` | Real Framework SDK execution, the 5 x 4 matrix, forwarding and local MCP transports. |
| `tests/release/` | Tutorials, packaging, artifacts, documentation and quarantine-absence gates. |
| `tests/composition/` | Tool/Skill identity, conflicts, precedence, reuse and composition coherence. |
| `tests/integration_conformance/` | Framework and Graph boundary profiles and state projection. |

There is no quarantine, dynamic loader or routed historical test body. Durable
assertions from the former modules now live with their owner; redundant and
layout-specific assertions were removed.

## Coverage policy

Core coverage is blocking at 100% and omits both the public Bedrock facade and
its internal package:

```powershell
python -m pytest -q --cov=agentic_systems --cov-config=pyproject.toml --cov-report=term-missing
```

Bedrock has an independent upward-only ratchet:

```powershell
python -m pytest -q tests/providers/bedrock `
  --cov=agentic_systems.providers.bedrock_runtime `
  --cov=agentic_systems.providers.bedrock `
  --cov-config=.coveragerc-bedrock `
  --cov-report=term-missing
```

Current verified status:

- Full suite: 469 passed; 15 deterministic notebooks execute under pytest.
- Strands MCP: native stdio and Streamable HTTP transports execute locally.
- Core: 100.00% over 7,060 statements.
- Bedrock: 100% over 620 statements; `fail_under = 100`.
- Core branches: 98.13% measured; `fail_under = 98.1`.
- Provider branches: 97.76% measured; `fail_under = 97.7`.
- Framework branches: 98.88% measured; `fail_under = 98.8`.
- Ruff: green over `src`, `tests`, and the local tutorial MCP fixture.
