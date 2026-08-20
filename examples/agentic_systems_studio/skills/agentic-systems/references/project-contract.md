# Portable application contract

Use one manifest or typed SystemSpec as the source of truth for identities,
stages, capabilities, assets and topology.

Reference layout:

    application/
      manifest.json
      pyproject.toml
      .env.example
      README.md
      src/application/
        tools.py
        skills.py
        agents.py
        system.py
        environment.py
        evals.py
        settings.py
      skills/
        codex-skill/SKILL.md
        runtime/runtime-skill.json
      assets/system.mmd
      data/app.db
      notebooks/00_walkthrough.ipynb
      tests/test_contract.py
      tests/test_execution.py

The manifest must identify Agentic Systems version, system identity, ordered
stages, execution plan, required capabilities, provider/framework policy and
assets. Mermaid node identities must match executable stage identities.
Notebook, CLI and UI must call the same constructor used by tests.

A product bundle may contain nested system bundles. Each nested bundle must be
independently understandable and include its manifest, Mermaid, runnable entry
point, notebook, tests, environment template and credential-free configuration.
The top bundle adds a catalog, composition examples, SQLite inventory and
checksums.
