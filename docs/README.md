# Agentic Systems documentation · 2.1.9

Agentic Systems composes executable Tools, model-backed agent actors and graph-based agent actuators into inspectable, evaluable Systems. Start with the [progressive README](../README.md): each interaction explains the request, the meaning of its answer, the declarations that produce it and the recorded work behind it.

This documentation targets the published **2.1.9** release. See its [validation scope](VALIDATION_219.md) for exact-artifact acceptance; historical reports retain their original identities.

## Choose the next concept you need

| Your question | Read next |
|---|---|
| How do I obtain my first result? | [Install](../INSTALL.md), [first Tool](ONBOARDING_FIRST_RUN.md) |
| What do the objects do? | [Concepts](CONCEPTS.md) |
| How do I connect capabilities? | [Graphs](GRAPHS.md), [composition](COMPOSITION_LAWS.md) |
| How do I configure provider, model and actor execution? | [Integrations](INTEGRATIONS.md), [runtime controls](RUNTIME_SCHEDULER_214.md) |
| What do compile/run/arun do? | [Execution](EXECUTION.md) |
| How do I read outputs, Tool calls and failures? | [Results](RESULTS.md) |
| How do I check outputs and trajectories? | [Evaluation](EVALUATION.md) |
| When do I need successive records? | [Environment](ENVIRONMENT_214.md) |
| How do reference data, history and sessions differ? | [Context and Memory](CONTEXT_MEMORY.md) |
| Where are the signatures? | [API surface](API_214_SURFACE.md) |
| What changed from 2.1.8? | [Migration](MIGRATION_218_TO_219.md) |

## Learn by executing

[Core lessons](../tutorials/README.md) introduce Tools, Skills, Agents and Systems. Add Environment for episodes, Context/Memory for reference information and history, or Eval for acceptance. These are independent choices; an application does not need every object.

Use the [notebook index](NOTEBOOKS.md) for executable sources and generated reading views. The [example catalog](../examples/README.md) groups applications by task. The time-series [application source](../examples/time_series_discovery_219/ADA_Time_Series_Discovery_219_Core.ipynb) targets 2.1.9; its [recorded-output viewer](../examples/time_series_discovery_219/Recorded_Outputs.ipynb) intentionally preserves historical 2.1.8 runs.

## Build with ChatGPT or Codex

The [version-matched authoring Skill](../skills/agentic-systems/SKILL.md) is bundled in the SDK. The [CLI](CLI.md) can inspect, install or export it. It helps coding assistants author applications; runtime `toolkit.skill(...)` groups an application's Tools.

[Download the 2.1.9 authoring Skill](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.9/agentic-systems-skill-2.1.9.zip) or export the ZIP from the installed SDK. Installation/export does not automatically register a personal ChatGPT Skill. Notebooks and optional Studio/ADA packages remain separate resources.

## Advanced references and evidence

[Actor contracts](ACTOR_CONTRACTS.md) document existing advanced options. The 2.1.9 introductory path uses Tool validation, instructions and external Evals without explicit Agent contracts or policies. Broader control-object validation is planned for 2.1.10.

[Release notes](RELEASE_NOTES_219.md), [validation scope](VALIDATION_219.md) and [publishing](RELEASE_PUBLISHING.md) describe current status. Historical acceptance, including [2.1.8 validation](VALIDATION_218.md), retains its recorded version and hashes. Reports and snapshots in revisions/ and examples/history/ are archival. Stable `_214` guide URLs remain available; they do not introduce a second supported grammar.
