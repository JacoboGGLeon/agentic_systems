# Release and verification status · Agentic Systems 2.1.4

The 2.1.4 SDK is published on [PyPI](https://pypi.org/project/agentic-systems/2.1.4/). Published wheel and source artifacts are immutable. Documentation and mutation-quality improvements in the open PR are candidate repository changes, not replacements for published artifacts.

[PR #15](https://github.com/JacoboGGLeon/agentic_systems/pull/15) verifies stronger contracts and an audited equivalent-aware gate. Before the current documentation updates, [quality](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/41954709455) passed Python 3.10–3.14 and [mutation quality](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/41954709456) passed with 2,360 detected mutants, six reviewed equivalents and zero unresolved cases out of 2,366. These results belong to their recorded commit; changed documentation must receive its own validation.

Graph is the sole public graph builder. compile prepares; run/arun execute; RunResult retains evidence. Native, OpenAI Agents and Strands are actor frameworks, independent of providers. Context, Memory, Environment and Eval retain their distinct contracts. Borrowed Bedrock sessions explicitly select IAM, remain outside serialized business data and are serialized for shared toolkit invocation; their owner controls external use and lifetime. ADA remains a separate diagnostics package.

Historical campaigns retain original hashes, budgets, failed attempts and acceptance scope. [Original dev8 report](../revisions/2.1.4/grammar-dev8/REPORT.md), [provider corrections](../revisions/2.1.4/problem-fixes/01/REPORT.md) and [Ollama connection verification](../revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md) must not be treated as blanket live acceptance of newer bytes.

Real IAM/ADA, GPU vLLM, exact provider edge cases such as Bedrock nullable outputs, and full model-backed Studio behavior require their own prepared environments and explicit evidence. Offline configuration or fixture conversation tests do not certify enterprise authentication or every UI control.

No durable recovery, general rollback, full RL API or ADA Studio wallet is claimed. [English notebook index](NOTEBOOKS.md) · [API](API_214.md) · [Signatures](API_214_SURFACE.md).
