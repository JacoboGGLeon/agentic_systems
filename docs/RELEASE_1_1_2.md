# Agentic Systems 1.1.2

Version: `1.1.2`.

## User Impact

This maintenance release makes Agentic Systems easier to trust and maintain
without changing how users call it. Existing code keeps the same 111-symbol
public API, the same `agentic_systems.providers.bedrock_runtime` import route and
the same public `BedrockRuntime` methods and signatures. No application
migration is required from 1.1.1-compatible code.

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

The detailed test mapping is recorded in
[TEST_MIGRATION_1_1_2.md](TEST_MIGRATION_1_1_2.md).

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
