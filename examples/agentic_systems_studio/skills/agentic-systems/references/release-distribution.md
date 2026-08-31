# Release and distribution contract

Treat public versions, tags and artifact hashes as immutable identities. A
change to runtime behavior, public contracts or packaged application material
requires a new version and renewed evidence; do not move a published tag or
replace an artifact under an existing public version.

The product has three complementary delivery surfaces:

1. PyPI publishes the `agentic-systems` wheel and source distribution. These
   contain the computational grammar, normalized runtime and CLI.
2. The GitHub release publishes the matching Studio ZIP, Codex/ChatGPT skill
   ZIP, offline enterprise delivery and specialized validation bundles.
3. Each application bundle owns its notebooks, `.env.example`, tests, entry
   point and documentation while depending on the exact Python distribution.

Before publishing, install the wheel non-editably in an isolated environment
and execute public API, CLI and deterministic smoke tests from outside the
repository. Validate wheel and sdist metadata, archive membership, checksums,
secret absence and Python-version support. Live attestations must identify the
same version, commit and wheel SHA256 as the artifact being published.

Studio portability means changing configuration rather than application code.
Its `.env` may configure OpenAI, Ollama, Bedrock API-key or AWS credential-chain,
and vLLM routes. The UI may select any configured provider and compatible
framework for the session, but credentials remain owned by `.env` or the host
environment. `python-runtime` is a deterministic control, not a language model.

A shareable skill ZIP must contain one top-level `agentic-systems/` directory,
its `SKILL.md`, referenced resources, UI metadata, scripts and required assets.
Run the skill validator on the source directory and inspect the archive before
publishing it.
