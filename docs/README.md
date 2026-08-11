# Documentation

This directory is the canonical documentation hub for Agentic Systems. Start
with the shortest path that matches your goal; historical evidence is kept
separate from current product guidance.

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
| Computational model | [Computational Grammar](COMPUTATIONAL_GRAMMAR.md) |
| Package structure and ownership | [Architecture](ARCHITECTURE.md) |
| Provider, runtime and framework boundaries | [Boundaries](BOUNDARIES.md) |
| Result and final-answer invariants | [RunResult Final Answer](RUNRESULT_FINAL_ANSWER.md) |
| Static system inspection | [Static System Inspection](STATIC_SYSTEM_INSPECTION.md) |

## Reference

| Topic | Document |
|---|---|
| Complete public Python surface | [API Reference](API.md) |
| Diagnostics and inspection commands | [CLI Reference](CLI.md) |
| Migration from 1.0 | [Migration 1.0 to 1.1](MIGRATION_1_0_TO_1_1.md) |

## Engineering And Release

| Topic | Document |
|---|---|
| Contribution and validation gates | [Contributing Checklist](CONTRIBUTING_CHECKLIST.md) |
| Current 1.1.2 release evidence | [Release 1.1.2](RELEASE_1_1_2.md) |
| Test migration record | [Test Migration 1.1.2](TEST_MIGRATION_1_1_2.md) |
| Coverage scope and measurements | [Pytest Coverage Report](PYTEST_COVERAGE_REPORT.md) |
| Future work | [Roadmap](../ROADMAP.md) |

Checkpoint reports, ADRs and earlier release reports are historical records.
They explain why decisions were made, but they do not override current API,
installation or release guidance.

## Sources Of Truth

When documents appear to disagree, use this order:

1. `pyproject.toml` and `src/agentic_systems/api.py` define package metadata,
   optional extras and the public API inventory.
2. The current README, installation guide, API reference and CLI reference
   describe supported user behavior.
3. The current release report records the evidence for that release.
4. Checkpoints, ADRs and older release reports preserve historical context only.

Tests enforce the public inventory, compatibility signatures, Markdown
integrity and release claims that can be checked locally.

## Language Policy

Canonical reference, architecture and operational documents are written in
English. The tutorial learning path may use Spanish narration so it remains
approachable to its intended audience. Python identifiers, commands,
environment variables and contract terminology remain unchanged in either
language. A translation must preserve the same API names, behavior and evidence
boundary as the canonical reference.
