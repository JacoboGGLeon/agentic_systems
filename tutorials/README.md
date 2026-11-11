# Tutorials · Agentic Systems 2.1.7

Start with core/00 and run cells in order. Each lesson exposes input → process → output and executable assertions. Use `import agentic_systems as toolkit`; LangGraph is the sole graph orchestrator.

Install the SDK and extras using [installation instructions](../INSTALL.md). Core lessons do not require Studio unless explicitly stated. Linked local Skill resources require the repository. The wheel does not contain these notebooks.

Follow **Start → Tools/Skills → Agent → System → Environment → Eval**, then Context/Memory and results. Explore providers, frameworks and execution controls afterward. Declarations are visible rather than hidden in an imported experiment.

[Complete English notebook index and Markdown reading views](../docs/NOTEBOOKS.md).

- [Core](core/00_start.md): deterministic operations, composition, episodes, evaluation and evidence.
- [Providers](providers/00_python.md): Python offline; OpenAI, Bedrock and Ollama live profiles; vLLM/GPU preparation.
- [Frameworks](frameworks/01_langgraph.md): orchestration, native/OpenAI Agents/Strands actors and local continuation.
- [API](api/01_runtime_framework.md): independent runtime/framework selection, contracts, fixture judges and shared deadlines.

Provider configuration is not proof of live access. A fixture judge verifies a protocol, not language-model reasoning. MCP/A2A uses a separate local-services profile. A timeout does not kill a worker or undo external effects. Continuations are process-local.

[API signatures](../docs/API_214_SURFACE.md) · [Examples](../examples/README.md) · [Documentation](../docs/README.md).
