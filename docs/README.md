# Documentation

This directory contains only current product documentation for Agentic Systems.
Release history lives in `CHANGELOG.md`, published evidence lives in GitHub
Releases, and superseded plans remain available through Git history.

## Start Here

| Goal | Document |
|---|---|
| Understand the product and its public model | [Project README](../README.md) |
| Install the package and optional backends | [Installation](../INSTALL.md) |
| Run the first provider-backed notebook | [First Run Onboarding](ONBOARDING_FIRST_RUN.md) |
| Learn through executable notebooks | [Tutorials](../tutorials/README.md) |

## Concepts And Boundaries

| Topic | Document |
|---|---|
| Computational grammar, semantics and API ownership | [Computational Model](COMPUTATIONAL_MODEL.md) |
| Package structure, namespace ownership and placement | [Architecture](ARCHITECTURE.md) |
| Runtime, Provider, Framework and Graph boundaries | [Runtime And Framework Contracts](RUNTIME_AND_FRAMEWORK_CONTRACTS.md) |
| Result, final-answer and serialization invariants | [RunResult Contract](RUNRESULT_CONTRACT.md) |
| Tool and Skill composition | [Composition Laws](COMPOSITION_LAWS.md) |

## Reference

| Topic | Document |
|---|---|
| Complete public Python surface | [API Reference](API.md) |
| Diagnostics and inspection commands | [CLI Reference](CLI.md) |

## Engineering

| Topic | Document |
|---|---|
| Contribution and validation gates | [Contributing Checklist](CONTRIBUTING_CHECKLIST.md) |
| Version history | [Changelog](../CHANGELOG.md) |
| Future work | [Roadmap](../ROADMAP.md) |

## Sources Of Truth

When documents appear to disagree, use this order:

1. `pyproject.toml` and `src/agentic_systems/api.py` define package metadata,
   optional extras and the public API inventory.
2. The current README, installation guide and API/CLI references describe
   supported user behavior.
3. Current contract documents define cross-module invariants and boundaries.
4. `CHANGELOG.md` records version history; GitHub Releases record published
   artifact evidence.

Tests enforce the public inventory, compatibility signatures, Markdown
integrity and release claims that can be checked locally.

## Language Policy

Canonical reference, architecture and operational documents are written in
English. The tutorial learning path may use Spanish narration so it remains
approachable to its intended audience. Python identifiers, commands,
environment variables and contract terminology remain unchanged in either
language. A translation must preserve the same API names, behavior and evidence
boundary as the canonical reference.