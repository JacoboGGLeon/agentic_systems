# Concepts and boundaries · dev8

Tool is a typed operation; Skill groups Tools/instructions. Agent owns a capability
or actor; System coordinates the application; Environment supplies episodes.
Every composition uses toolkit.Graph, the original LangGraph StateGraph with one
public name. compile prepares without inference; run/arun return RunResult.
There is no public check, StateGraph alias, Limits, Action or Runtime.

State is working data; Context is domain data/sources; Memory contains bounded
local episodes; lineage records observed work. Tools and nodes request the same
*, context: toolkit.Context. Use named node functions with explicit projections.
A single-parameter Tool with input_schema receives that Pydantic model.

Eval gives each case a private view of toolkit Memory; within one Environment
case its episodes share that view. It does not isolate files/services/SDK sessions.
Environment exposes state/observe/update/stop/max_steps, not a full RL API.
Reward can be an explicit state metric in update; it does not train a policy.

The 15 core words are tool, skill, load_skill, Agent, System, Environment, Eval,
RunResult, Context, Memory, pause, runtime, framework, model_artifact, model_server.
Graph, START, END, Command and Send are original LangGraph objects.
