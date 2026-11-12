# Execution lifecycle · 2.1.9

Definitions describe work. compile() prepares and validates integrated structure, without business execution or model inference. The compiled program executes work and returns RunResult. Direct owner.run() compiles internally.

| Object | compile | run | arun | inspect |
|---|---|---|---|---|
| Agent / System | compile() | run(input=None, *, timeout_s=None) | arun(input=None, *, timeout_s=None) | inspect() |
| Environment / Eval | compile() | run(*, timeout_s=None) | arun(*, timeout_s=None) | inspect() |
| Tool | Not exposed | run(input=None) | arun(input=None) | inspect() |

Environment uses configured records; Eval uses configured cases. Skills and Context are not executable owners.

```python
program = agent.compile()  # agent must already be declared
result = program.run({"value": 3})
print(result.status, result.ok, result.data)
print(result.evidence())
```

This fragment continues a declared Agent; for a standalone program use [first result](ONBOARDING_FIRST_RUN.md). arun is an async interface, implemented with thread delegation for compiled programs. Graph edges govern parallel branches; awaiting one arun call does not create branches.

Constructor/compilation errors identify invalid declarations and can raise exceptions. Operational failures are represented by unsuccessful RunResults. Inspect status, errors and children; ok=True is not universal truth. A paused result is not completed even when ok=True.

## Pause and resource lifetime

Use toolkit.pause inside a graph callback. Resume through program.resume(paused_result, value), or await program.aresume(...), on the **same compiled object in the same process**. Eval does not allow pause. Completed work is retained; the interrupted callback can restart, so isolate external effects or make them idempotent. [Executable pause lesson](../tutorials/frameworks/01_langgraph.md).

run(timeout_s=...) sets a shared root deadline; children inherit remaining time. Actor runtime supplies local timeout/retry/backoff/concurrency/turn/tool/token controls. Timeouts do not forcibly stop threads, undo effects or provide durable recovery. [Detailed controls](RUNTIME_SCHEDULER_214.md).

[Results](RESULTS.md) · [Evaluation](EVALUATION.md)
