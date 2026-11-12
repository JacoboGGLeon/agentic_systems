# Execution and evidence · 2.1.9

Agent/System: compile(), run(input=None, *, timeout_s=None), arun(input=None, *, timeout_s=None), inspect(). Environment/Eval have the same methods but run/arun use configured records/cases, not a supplied input. Tool has run/arun(input=None), inspect(), no public compile.

compile prepares without inference. owner.run compiles internally. The compiled object also exposes resume(paused,value) and aresume, requiring the same program/process. Eval does not allow pause. arun is an asynchronous interface, not a declaration of graph parallelism.

| RunResult method | Return |
|---|---|
| evidence() | dict, primary JSON-compatible export including children |
| to_dict() | dict, compatibility alias with unchanged schema/redaction |
| trace() | dict |
| human_results() | str |
| lineage() | Object with explain/render/to_dict/to_prompt_context |
| walk() | Generator of root and descendant RunResults |
| check_invariants() | Object with ok/issues/to_dict |

Use data/text/final for recorded outputs; status/ok/errors/validation for outcome; execution_id/parent_execution_id/children for hierarchy; messages/tool_events/raw_responses for interactions; usage/engine/model/mode for execution metadata; interrupts/continuation for local pauses; meta/trace_schema_version for schema metadata. Invariants are not business acceptance; event membership is not a concurrency timeline.

Eval independently targets Agent/System/Environment. Cases support expected={"ok": bool, "data": exact_dict}; custom checks receive (result, case) and return {"ok": bool} with optional issues/metrics. Expected failures require expected={"ok": False}. Eval is fail-fast; independent negative scenarios may need separate Evals. Memory is isolated per case, external services/sessions are not.

Run assets/eval_recipes.py for five complete deterministic cases with positive and rejecting controls: output, required Tool, branch selection, expected failure and episodic stopping. No LM requests are involved.
