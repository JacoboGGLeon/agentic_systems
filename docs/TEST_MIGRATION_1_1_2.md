# Test Migration Map

Release: `1.1.2`.

## Method

Each quarantined module was reviewed semantically before removal. Unique public
contracts moved to `tests/api`, private branches moved to `tests/unit`, Provider
behavior moved to `tests/providers`, and packaging/tutorial evidence moved to
`tests/release` or `tests/contracts`. Coverage was used as evidence, not as a
substitute for assertions.

## Final status

- Baseline: 53 physical files / 52 dynamically routed modules.
- Final: 0 routed modules and 0 quarantine files.
- Dynamic loader calls: 0.
- Ruff quarantine exclusions: 0.
- Public API symbols: 111, unchanged.
- Full suite: 381 tests.

## Destination map

| Original responsibility | Final owner |
|---|---|
| CLI, Tool, Skill, Agent and public runtime behavior | `tests/api` |
| Scheduler, renderers, helpers, factories and private branches | `tests/unit` |
| Base, OpenAI, Python Direct and Bedrock Provider contracts | `tests/providers` |
| Tutorials, artifacts, packaging and quarantine absence | `tests/release` |
| Public inventory, optional-import boundary and Bedrock signatures | `tests/contracts` |

Broad checkpoint and coverage modules were not copied wholesale. Their durable
assertions were parameterized or assigned to the production owner; redundant,
layout-specific and speculative assertions were deleted.

## Bedrock closure

The final Bedrock modules were decomposed into explicit suites for models,
tools, Converse, OpenAI compatibility, validation, facade behavior and
LangGraph. Production retains `providers/bedrock_runtime.py` as the public
facade and places implementation components under `providers/bedrock/`.

Core coverage remains 100% over 6,194 statements. Bedrock is measured separately
over the facade and internal package: 53.17% measured, with a blocking ratchet of
53.1%.

## Retirement rule retained

No new quarantine or dynamic loader may be introduced. The release contract
asserts that both paths are absent, and Ruff runs over all of `src` and `tests`.
