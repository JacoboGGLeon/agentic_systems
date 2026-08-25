# Portable application contract

Use one manifest or typed SystemSpec as the source of truth for identities,
stages, capabilities, assets and topology.

Reference layout:

    application/
      pyproject.toml
      .env.example
      README.md
      app.py
      src/application/
        tools.py
        system.py
        settings.py
      notebooks/
        00_conversational_system.ipynb
        01_launch_application.ipynb
      tests/
        test_contract.py
        test_execution.py

The typed configuration or manifest must identify the Agentic Systems version,
system identity, execution plan, required capabilities and provider/framework
policy. The direct notebook, presentation adapter and tests must call the same
constructor.

A product bundle must be independently understandable and include its runnable
entry point, direct notebook, tests, `.env.example`, credential-free
configuration, manifest and checksums. Do not duplicate the agentic logic in
the UI and do not persist credentials or raw provider reasoning.
