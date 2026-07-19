# Agentic Systems progress

## Current Status

The repository is clean around the canonical `agentic_systems` package.

Closed cleanup phases:

```text
1. examples/ root removed
2. src/agentic_systems/examples removed
3. demo exports removed from public API
4. tutorials/tools removed
5. tutorials made the only pedagogical route
6. wheel/sdist packaging constrained to src/agentic_systems
7. PUBLIC_API deduplicated and validated
8. root docs aligned with Agentic Systems naming
```

## Canonical Tree

```text
src/agentic_systems/
docs/
tests/
tutorials/
dist/
```

## Public Import

```python
import agentic_systems as toolkit
```

Removed public names:

```text
demo_case
run_tools
configure_tutorial_environment
```

## Validation

Latest full validation:

```text
pytest: 354 passed
coverage: 100.00%
compileall: OK
wheel smoke: OK
```

## 1.1 Checkpoints

| Checkpoint | Status | Primary evidence |
|---|---|---|
| 1.1.0 Grammar audit | complete | `docs/checkpoints/1.1.0_grammar_audit.md` |
| 1.1.1 Normative semantics | complete | `docs/COMPUTATIONAL_GRAMMAR.md`, `docs/SEMANTICS.md` |
| 1.1.2 RunResult invariants | complete | `docs/checkpoints/1.1.2_run_result_invariants.md` |
| 1.1.3 Tool and Skill composition | complete | `docs/checkpoints/1.1.3_tool_skill_composition.md` |
| 1.1.4 Runtime and Provider substitution | complete | `docs/checkpoints/1.1.4_runtime_provider_substitution.md` |
| 1.1.5 Framework and Graph boundary | complete | `docs/checkpoints/1.1.5_framework_graph_boundary.md` |
| 1.1.6 Systems, Environments, and Evals | complete | `docs/checkpoints/1.1.6_system_environment_eval.md` |
| 1.1.7 Execution Context decision | complete | `docs/checkpoints/1.1.7_execution_context_decision.md` |
| 1.1.8 Static system inspection | complete | `docs/checkpoints/1.1.8_static_system_inspection.md` |

Checkpoint 1.1.4 introduces a shared base conformance suite and explicit
capability profiles for python-runtime, openai-runtime, vllm-runtime, and
bedrock-runtime. Checkpoint 1.1.5 distinguishes the real LangGraph adapter from
OpenAI Agents-style and Strands declarative identities, and separates portable
Graphs from framework-native objects. Checkpoint 1.1.6 separates composition,
transition, episode, and verification ownership and adds explicit replay
classification. Checkpoint 1.1.7 keeps Execution Context conceptual, with no new
public/internal object or compatibility change. Validation totals are recorded
in the checkpoint reports. Checkpoint 1.1.8 adds a non-executing structured and
human inspection projection with actionable diagnostics.
