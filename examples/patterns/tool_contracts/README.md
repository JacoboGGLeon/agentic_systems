# Tool Contracts — API 2.1.3

Pydantic input/output schemas, direct/async deterministic Tool and a controlled invalid input.

```python
from examples.tool_contracts.example import run

result = run()
result
```

Synthetic JSON input → canonical SDK computation/configuration → asserted output and JSON evidence.

Código:
- [Runnable example](../../../examples/tool_contracts/example.py)
- [Walkthrough](../../../examples/tool_contracts/README.md)

Validación: **Offline ejecutado**. Pydantic input/output schemas, direct/async deterministic Tool and a controlled invalid input. Final artifact binding is recorded in implementation evidence. No real inference.

- [Measured offline report](../../../revisions/2.1.3/closeout-evidence/REPORT.md)
- [Exact artifact and evidence hashes](../../../revisions/2.1.3/implementation-evidence/manifest.json)
