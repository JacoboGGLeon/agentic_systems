# Agentic Systems 1.1.1 Unpublished Maintenance Checkpoint

Version target: `1.1.1`.

Status: this checkpoint was not tagged or published to PyPI. It is retained as
historical engineering evidence and must not be read as the current installation
or release contract. Agentic Systems 1.1.2 supersedes it.

## Scope Recorded At The Checkpoint

The work reduced accidental surface and aligned packaging, documentation,
tutorials and tests without adding public API symbols.

## Evidence Recorded At The Checkpoint

- The then-current pytest suite passed.
- Core coverage was 100%; `providers/bedrock_runtime.py` was excluded from that
  percentage.
- 13 deterministic notebooks executed and 5 provider notebooks were checked
  statically.
- The wheel contained the library and CLI but not repository tutorials.
- The public inventory remained 111 symbols.

These statements describe the checkpoint tree, not the final 1.1.2 artifact.
Current evidence lives in [RELEASE_1_1_2.md](RELEASE_1_1_2.md).

## External Evidence Boundary

No live OpenAI, Bedrock, vLLM, Strands SDK or OpenAI Agents SDK execution was
claimed by the automated checkpoint suite.

## Surface Decisions Carried Into 1.1.2

- `build_single_agent_step_graph` and `PUBLIC_API` are not top-level attributes.
- Optional extras `vll` and `tutorials` were removed; `vllm` remains the
  supported vLLM extra.
- Tutorial dependencies belong to the repository development environment.
