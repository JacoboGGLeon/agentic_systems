# Documentation

This directory is the canonical documentation hub for Agentic Systems. Start
with the shortest path that matches your goal. Current product contracts,
architectural decisions, historical evidence and future proposals are separate
layers.

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
| System, Environment and Eval ownership | [System, Environment And Eval Semantics](SYSTEM_ENVIRONMENT_EVAL_SEMANTICS.md) |
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
| Active maintenance checkpoint | [Checkpoint 1.1.3](CHECKPOINT_1_1_3.md) |
| Contribution and validation gates | [Contributing Checklist](CONTRIBUTING_CHECKLIST.md) |
| Current 1.1.2 release evidence | [Release 1.1.2](RELEASE_1_1_2.md) |
| Future work | [Roadmap](../ROADMAP.md) |
| Accepted architectural decisions | [ADR Index](adr/README.md) |
| Unaccepted design proposals | [RFC Index](rfcs/README.md) |
| 1.1 development history | [Development Checkpoints](history/1.1-development-checkpoints.md) |
| Earlier 1.1 release evidence | [Release History](history/RELEASE_HISTORY_1_1.md) |

ADRs explain accepted decisions, RFCs describe unaccepted proposals and history
preserves superseded evidence. None overrides current API, installation,
contract or release guidance.

## Sources Of Truth

When documents appear to disagree, use this order:

1. `pyproject.toml` and `src/agentic_systems/api.py` define package metadata,
   optional extras and the public API inventory.
2. The current README, installation guide and API/CLI references describe
   supported user behavior.
3. Current contract documents define cross-module invariants and boundaries.
4. The current release report records evidence for the published artifact.
5. ADRs, RFCs and history preserve rationale or context only.

Tests enforce the public inventory, compatibility signatures, Markdown
integrity and release claims that can be checked locally.

## Language Policy

Canonical reference, architecture and operational documents are written in
English. The tutorial learning path may use Spanish narration so it remains
approachable to its intended audience. Python identifiers, commands,
environment variables and contract terminology remain unchanged in either
language. A translation must preserve the same API names, behavior and evidence
boundary as the canonical reference.