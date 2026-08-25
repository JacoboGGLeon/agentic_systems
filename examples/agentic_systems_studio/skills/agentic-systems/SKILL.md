---
name: agentic-systems
description: Design, scaffold, implement or audit portable Agentic Systems 2.1 applications, including deterministic tools, runtime Skills, agents, system composition, environments, evals, provider/framework selection and normalized RunResult contracts.
metadata:
  short-description: Build industrial Agentic Systems 2.1 apps
---

# Agentic Systems 2.1

Build the requested application from one explicit system declaration. Use that
declaration to keep source, public API usage, notebooks, tests, documentation
and bundles coherent.

## Conceptual boundaries

- A Tool is a deterministic operation.
- A runtime Skill packages tools, prompts, contracts and policy for an Agent.
- A Codex/ChatGPT skill is an assistant instruction package such as this folder.
  It can generate or modify applications; it is not the runtime Skill executed
  by an Agent.
- An Agent is one computation unit and owns its internal pipeline.
- A System connects computation units through an external execution plan.
- An Environment supplies episodes and steps through time.
- An Eval measures an Agent or System directly, or observes it through episodes.
- RunResult is the normalized public result at every execution boundary.

Read references/conceptual-model.md when architecture or terminology is part of
the request.

## Workflow

1. Capture explicit requirements, uncertainty, data boundaries and acceptance
   evidence. Do not invent provider access, external authority or deployment.
2. Choose the smallest topology that demonstrates the requested behavior.
   Put parsing, arithmetic, validation and policy rules in deterministic Tools.
   Use reasoning agents only where judgment or language interpretation is needed.
3. Select provider and framework independently. Check the installed compatibility
   surface before promising a combination. Read references/provider-framework.md
   for provider selection, credentials and live testing.
4. Assemble through the public toolkit grammar: toolkit.tool, toolkit.skill,
   toolkit.agent or system.agent, toolkit.system, toolkit.environment and
   toolkit.eval. Keep execution composition on the System.
5. Call inspect before live execution. Verify deterministic behavior offline,
   then test only explicitly configured live providers. Preserve one normalized
   RunResult and its child lineage.
6. Update the declaration first when topology changes, then regenerate diagrams,
   manifests and derived assets. Read references/project-contract.md for the
   required application structure. Reject python-runtime when any declared stage
   is a reasoner or reviewer; it is an operator runtime, not a language-model
   provider.
7. Use references/testing.md for contract, notebook, provider/framework and
   bundle acceptance gates.

Never write credentials into source, notebooks, manifests, SQLite or bundles.
Do not silently fall back to another provider or framework in a conformance
test. Report installed, configured, compatible and live-verified as separate
states.
