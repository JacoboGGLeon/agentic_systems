# Test matrix

The current test files remain physically flat to avoid unnecessary churn in
fixture paths and historical checkpoint names. They are classified by intent so
future checkpoints can add tests in the right area before any larger test-tree
move.

| Category | Current pattern | Purpose |
|---|---|---|
| Unit | `test_tool_*`, `test_agentic_systems_api.py`, `test_compare_*` | Core behavior for tools, agents, results and contracts. |
| Providers | `test_checkpoint_08*`, `test_bedrock_*`, `test_checkpoint_00_decoupling.py` | Engine/provider compatibility and optional dependency behavior. |
| Integrations | `test_checkpoint_11*`, `test_checkpoint_12*`, `test_normalized_graph_output.py`, `test_multi_agent_state_contract.py` | LangGraph/OpenAI Agents/graph-facing behavior. |
| Tutorials | `test_notebook_*`, `test_tutorial_*`, `test_checkpoint_04k*`, `test_checkpoint_10c*`, `test_checkpoint_12b*`, `test_checkpoint_14b*` | Notebook syntax, imports and tutorial package structure. |
| Regression | `test_checkpoint_*` | Historical behaviors that must not regress while the repo is cleaned. |

Rule for Checkpoint 1 onward: add new scheduler/runtime tests using explicit
names such as `test_runtime_scheduler_config.py` and only move the tree when
all fixture root assumptions have been removed.
