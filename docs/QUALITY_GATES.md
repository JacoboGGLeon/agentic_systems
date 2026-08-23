# Triple Quality Gate

Agentic Systems 2.0.1 uses three blocking gates over the same release candidate.
Passing unit tests alone is not a release certification.

## Sources of truth

- `src/agentic_systems/registry.py` owns providers, frameworks, capabilities,
  dependencies, environment inputs and all 20 compatibility pairs.
- `src/agentic_systems/schemas/` owns strict persisted contracts, execution
  limits, normalized output and live-attestation schemas.
- `quality/live-profiles.json` partitions the canonical matrix by execution
  environment; its union must equal the registry and may not invent pairs.
- `.github/workflows/quality.yml`, `live-quality.yml`, `mutation.yml` and
  `release.yml` execute the gates. Presentation layers never maintain another
  compatibility list.

The runtime identifiers retained for 2.0 compatibility are
`python-runtime`, `openai-runtime`, `ollama-runtime`, `bedrock-runtime` and
`vllm-runtime`. The four framework identifiers are `native`, `langgraph`,
`openai-agents` and `strands`.

## Production gate

The pull-request gate runs Ruff, formatting, strict and baseline-ratcheted
Pyright, Import Linter, architecture checks, complexity, benchmarks, contracts,
the offline 20-pair matrix, coverage ratchets, dependency and license audits,
secret scanning, Studio tests, bundle builds, wheel/sdist checks and a clean
non-editable wheel smoke. Pull requests exercise Python 3.10 and 3.14; release
smokes exercise every Python version from 3.10 through 3.14.

Useful local commands:

```bash
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m pyright --project pyrightconfig.json
python scripts/check_pyright_baseline.py
lint-imports
python scripts/check_architecture.py
python scripts/check_complexity.py
python scripts/check_benchmarks.py
python scripts/check_licenses.py
python scripts/check_secrets.py
python -m pytest -q
python -m build --no-isolation
python -m twine check dist/*
```

The release workflow builds wheel and sdist once. Every protected live job and
Python smoke downloads those exact artifacts. PyPI Trusted Publishing uses only
the certified wheel and sdist; product ZIPs, SBOM, hashes and attestations are
attached to the GitHub release.

## Pydantic gate

`ExecutionLimits` is the only definition of execution bounds. Compatibility
facades delegate to it. Closed schemas reject unknown fields, use explicit
provider discriminators and never serialize `SecretStr` values. Persisted specs
carry `schema_version`; compatibility migrations are explicit and tested.

Hypothesis covers boundary values and JSON round trips. `RunResult` normalizes
public text, removes only a balanced leading native reasoning block, preserves
raw evidence separately and validates its own invariants. The API checksum uses
declared public fields and methods only, excluding members injected by Pydantic.

## POO and polymorphism gate

Agents and systems depend on small runner and adapter Protocols. Provider and
framework selection is confined to registries, factories, bootstrap code and
external adapters. Architecture checks reject concrete provider/framework
branches elsewhere and cross-adapter imports. Import Linter enforces dependency
direction. Contract tests substitute every provider and framework without
changing Agent/System inputs or normalized outputs.

Unsupported capabilities fail before execution. SDK errors become structured
errors with provider, framework, category, code and retryability. There is no
silent fallback; actual runtime identity is part of every result and live case.

## Live certification

Nightly and release jobs run OpenAI, Bedrock and Ollama from protected
credentials/services. Deterministic Python pairs run in the offline matrix.
vLLM is certified by the official Colab notebook in
`release/vllm_live_attestation_colab.ipynb`.

Each live case executes `inspect`, completion, agent, tool calling, structured
error and `RunResult` JSON round-trip scenarios. Text is not compared exactly;
contract invariants, identity and absence of fallback are compared. Evidence is
written as `agentic_systems.live-attestation.v1` with sanitized error details
and usage data.

The vLLM validator rejects evidence that:

- is older than 24 hours or dated in the future;
- identifies a different commit or wheel hash;
- omits or duplicates a provider/framework case or scenario;
- contains a failed case/scenario;
- omits CUDA, GPU, vLLM or model identity.

The release remains blocked until all 20 declared pairs have current evidence.
Published artifacts are immutable; a post-publication failure requires a new
corrective version.
