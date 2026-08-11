# Agentic Systems 1.1.2

Version: `1.1.2`.

## User Impact

This maintenance release makes Agentic Systems easier to trust and maintain
without changing how users call it. Existing code keeps the same 111-symbol
public API, the same `agentic_systems.providers.bedrock_runtime` import route and
the same public `BedrockRuntime` methods and signatures. No application
migration is required for code already compatible with the 1.1 public contract.

The package remains compatible with Python 3.10 through 3.14. Base imports stay
lazy with respect to boto3, OpenAI, LangGraph and other optional providers.

## What Changed

The test suite no longer depends on dynamically loaded quarantine modules. All
52 routed modules were either migrated to their owning API/unit/release domain
or removed after their evidence became redundant. The final tree has no legacy
loader, quarantine directory, Ruff exception or numeric legacy guardrail.

The public `providers/bedrock_runtime.py` module is now a small compatibility
facade. Models, identity, tools, Converse/direct execution, OpenAI compatibility,
validation and LangGraph responsibilities live in focused internal modules under
`providers/bedrock/`. The facade remains the owner of the public class, and
compatibility tests freeze its callable signatures.

The durable test-ownership map and published artifact hashes are recorded below.

## Release Evidence

- 381 tests pass with runtime warnings promoted to errors.
- 13 deterministic notebooks executed by pytest from clean kernels.
- 5 Provider notebooks checked statically for public-API, preflight and syntax contracts.
- Ruff passes over all `src` and `tests` without quarantine exclusions.
- Core coverage is 100% over 6,194 statements; Bedrock is explicitly outside
  that number.
- Separate Bedrock coverage is 53.17%, with a blocking `fail_under = 53.1`
  monotonic ratchet.
- The CI workflow gates Python 3.10 and 3.14 using
  `.[dev,bedrock,langgraph,openai]`, without installing VLLM.
- Build, `twine check` and isolated Python 3.14 wheel smoke are release gates.

The Bedrock suite uses fake clients and requires neither live AWS credentials nor
network access.

## Compatibility Guarantees

- `agentic_systems.__all__` remains exactly 111 symbols.
- No runtime feature or public callable was added.
- Public Bedrock imports and signatures are frozen by contract.
- Fake-client injection through `runtime.runtime` and monkeypatching through the
  historical provider route continue to work.
- Wheel, CLI and optional imports are validated outside the repository.

## Evidence Boundary

The automated suite proves deterministic behavior, packaging and adapter
contracts without claiming live OpenAI, Bedrock or vLLM execution. Provider
notebooks cross the external boundary only after an explicit readiness check;
an actionable skip is not reported as live evidence.

## Test Architecture Migration

The 1.1.2 cleanup started with 53 physical quarantine files representing 52
dynamically routed modules and ended with no loader, quarantine directory, Ruff
exception or numeric legacy guardrail.

| Evidence owner | Responsibility |
|---|---|
| `tests/api` | Public CLI, Tool, Skill, Agent and runtime behavior |
| `tests/unit` | Scheduler, renderers, helpers, factories and private branches |
| `tests/providers` | Base, OpenAI, Python Direct and Bedrock contracts |
| `tests/contracts` | Public inventory, optional imports and Bedrock signatures |
| `tests/release` | Tutorials, artifacts, packaging and quarantine absence |

Coverage remained split deliberately: core is 100% over 6,194 statements;
Bedrock is 53.17% with an upward-only blocking ratchet of 53.1%.

Published artifact SHA256 values:

```text
wheel  6F6087D01E3B74D4DF78E79F03B5015302B2692949880D2C0C14FB013AABD6F6
sdist  F46BD11632C458B74309A89152491D35C760F1F337CBD773336111BB59B4964D
```
