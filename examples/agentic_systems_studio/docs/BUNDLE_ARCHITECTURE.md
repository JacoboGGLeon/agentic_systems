# Bundle architecture

The distributable is deliberately recursive.

    agentic-systems-studio-2.0.1.zip
      manifest.json
      SHA256SUMS
      app.py
      src/agentic_systems_studio/
      skills/agentic-systems/
      notebooks/
      data/studio.db
      system-bundles/
        agentic-systems-creator.zip
        research-synthesis.zip
        decision-intelligence.zip
        incident-response.zip
        code-review.zip
        data-quality.zip
        prompt-security.zip
        meeting-action-center.zip
        quantitative-analysis.zip
        customer-support.zip

The top bundle is the Studio product and system-of-systems. Every nested ZIP is
a scaffolded standalone application with source, manifest, Mermaid, notebook,
tests, runtime and Codex skills, assets and SQLite. The outer manifest records
the SHA-256 of every nested bundle.

Composition is not packaging-only. The Studio composes the same nested
CompiledSystem objects through SequentialPlan or ParallelPlan and returns a
hierarchical RunResult. Consequently the diagram, runtime topology and bundle
inventory derive from the same catalog IDs.

Credentials are intentionally absent. The bundle includes only .env.example.
OpenAI, Ollama, Bedrock and vLLM configuration is injected at runtime.
