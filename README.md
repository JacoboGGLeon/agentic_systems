# Agentic Systems

A Python toolkit for composing deterministic Tools and model-backed agents in explicit LangGraph workflows, with contracts and shared execution evidence.

**Agentic Systems 2.1.8** adds a primary evidence export and a unified learning path. Use the matching versioned distribution, or the supplied frozen wheel during pre-publication acceptance. Use Python 3.10–3.14.

## First result

```python
import agentic_systems as toolkit

@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}

result = increment.run({"value": 3})
assert result.ok and result.data == {"value": 4}
print(result.data)
evidence = result.evidence()  # New in 2.1.8; to_dict() stays compatible.
```

No model account is required. [Installation](https://github.com/JacoboGGLeon/agentic_systems/blob/main/INSTALL.md) explains candidate wheels, extras and notebooks.

## Choose the pieces you need

| Piece | Purpose |
|---|---|
| Tool / Skill | Execute an operation / group capabilities and instructions |
| Agent(graph=...) | Organize an explicit capability workflow |
| Agent(runtime=...) | Execute an actor with its provider and framework |
| System | Coordinate application work through a graph |
| Environment | Execute episodes with observation, state updates and stopping |
| Eval | Independently check an Agent, System or Environment |
| Context / Memory | Supply domain information / retain bounded local episodes |

Graph is LangGraph's original StateGraph. Its nodes may be functions, Tools or units containing other graphs. It has no implicit Python provider. Frameworks implement actors; providers supply execution. Shared APIs do not imply universal feature parity.

## Build, run and inspect

Agent, System, Environment and Eval expose compile/run/arun/inspect. Agent/System accept an input; Environment/Eval use declared records/cases. compile prepares without business execution or inference. Direct run compiles internally.

```python
# After declaring an Agent or System:
program = system.compile()
result = program.run({"value": 3})
print(result.status, result.ok, result.data)
print(result.human_results())
evidence = result.evidence()       # dict
lineage = result.lineage()         # object; .to_dict() exports it
validation = result.check_invariants()
```

[Complete first program](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/ONBOARDING_FIRST_RUN.md) · [Execution](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/EXECUTION.md) · [Results](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/RESULTS.md)

## Authoring skill and CLI

The wheel bundles instructions, references and examples for coding assistants. This authoring skill differs from runtime toolkit.skill(...).

```bash
agentic-systems version
agentic-systems api
agentic-systems doctor
agentic-systems skill info
agentic-systems skill install
agentic-systems skill export agentic-systems-skill-2.1.8.zip
```

Install defaults to .agents/skills/agentic-systems. Install/export refuse existing destinations. The exported ZIP is suitable for manual import; copying it does not register a personal ChatGPT skill. doctor checks dependencies, not service access. There is no new/scaffolder command.

## Learn by task

- [Documentation entry point](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/README.md)
- [Concepts](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/CONCEPTS.md) and [graphs](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/GRAPHS.md)
- [Independent evaluation: five examples](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/EVALUATION.md)
- [Context and Memory](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/CONTEXT_MEMORY.md)
- [Providers/frameworks](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/INTEGRATIONS.md) and [actor contracts](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/ACTOR_CONTRACTS.md)
- [Tutorials](https://github.com/JacoboGGLeon/agentic_systems/blob/main/tutorials/README.md), [examples](https://github.com/JacoboGGLeon/agentic_systems/blob/main/examples/README.md), [signatures](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/API_214_SURFACE.md)
- [Migration from 2.1.7](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/MIGRATION_217_TO_218.md)

## Verification boundaries

ok=True describes declared acceptance, not universal truth. Tools, events and independent checks establish observed work. Memory and pause/resume are process-local; timeouts do not guarantee thread termination or rollback. Boto3 sessions are borrowed resources, excluded from configuration JSON; create a local session in each destination process.

Historical [2.1.7 AWS session checks](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/AWS_SESSION_VALIDATION_217.md) and [2.1.5 model campaigns](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/VALIDATION_215_20261108.md) retain their artifact identities. They do not certify the new wheel. EMR and distributed Spark remain unverified. The documented Bedrock required-nullable-field limitation remains; see [known issues](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/OPEN_ISSUES_214.md).

Studio, notebooks and the optional ADA diagnostics package are separate resources. [Release notes](https://github.com/JacoboGGLeon/agentic_systems/blob/main/docs/RELEASE_NOTES_218.md).
