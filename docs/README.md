# Agentic Systems documentation · 2.1.8

Start with one operation; add composition, model actors or episodes when they have a purpose. This documentation targets **2.1.8**. Historical acceptance belongs to its recorded version and artifact.

| Your question | Read next |
|---|---|
| How do I install and obtain a result? | [Install](../INSTALL.md), [first Tool](ONBOARDING_FIRST_RUN.md) |
| Which pieces do I need? | [Concepts and composition](CONCEPTS.md) |
| How do I connect steps and agents? | [Graphs](GRAPHS.md) |
| What do compile/run/arun return? | [Execution lifecycle](EXECUTION.md) |
| How do I inspect evidence and failures? | [RunResult reference](RESULTS.md) |
| How do I check an Agent or System? | [Independent evaluation](EVALUATION.md) |
| When do I need episodes? | [Environment](ENVIRONMENT_214.md) |
| How do Context, Memory and AWS sessions differ? | [Information and resource lifetime](CONTEXT_MEMORY.md) |
| Which model/framework should I configure? | [Integrations and boundaries](INTEGRATIONS.md) |
| What are the exact signatures? | [API signatures](API_214_SURFACE.md), [actor contracts](ACTOR_CONTRACTS.md) |
| What changed from 2.1.7? | [Migration](MIGRATION_217_TO_218.md) |

## Learn by executing

[Core lessons](../tutorials/README.md) progress from Tools to Agents and Systems. **Eval and Environment are independent branches**, not mandatory consecutive layers. Then explore Context/Memory, providers and frameworks. [Notebook index](NOTEBOOKS.md) links executable sources and generated reading views; [example catalog](../examples/README.md) is organized by task.

## Authoring and distribution

[CLI](CLI.md) supports version/api/doctor and skill info/install/export. The [authoring skill](../skills/agentic-systems/SKILL.md) is bundled in the wheel and can also be exported as a standalone ZIP. It differs from runtime `toolkit.skill(...)`. Notebooks and Studio are separate repository/release resources.

## Historical evidence and maintenance

[Release notes](RELEASE_NOTES_218.md) distinguish current changes from [2.1.7 AWS acceptance](AWS_SESSION_VALIDATION_217.md) and [2.1.5 live campaigns](VALIDATION_215_20261108.md). Files under revisions/ and examples/history/ are archival. Versioned campaign reports retain their provenance and are not instructions for the current API. Stable `_214` guide URLs remain available, but current conceptual references are linked above.
