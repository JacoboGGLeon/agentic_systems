# Contributing Checklist

Use this checklist before handing off changes. The documentation map defines the
current sources of truth; superseded work remains available through Git history.

## API And Ownership

```text
[ ] Public names are intentional, documented in docs/API.md and covered by compatibility tests.
[ ] Tutorials use `import agentic_systems as toolkit` when the public facade is sufficient.
[ ] Provider-agnostic primitives live in core; backend execution lives in providers.
[ ] Framework adaptation lives in integrations; the CLI remains diagnostic.
[ ] Optional SDKs are not required at base package import time.
```

## Documentation

```text
[ ] README, installation, API, CLI and tutorials use the same names and support claims.
[ ] Runnable Python examples parse and local Markdown links resolve.
[ ] Return values, failure behavior and external evidence boundaries are explicit.
[ ] Removed aliases and historical paths are not presented as current guidance.
[ ] Tutorial order agrees with tutorials/README.md.
```

## Local Validation

```bash
python -m ruff check src tests
python -m pytest -q -W error::RuntimeWarning
python -m pytest -q --cov=agentic_systems --cov-report=term-missing
python -m pytest -q --ignore=tests/release/test_tutorial_execution.py \
  --cov=agentic_systems \
  --cov-config=.coveragerc-core-branches \
  --cov-report=term-missing
python -m pytest -q tests/providers \
  tests/integration_conformance/test_provider_conformance.py \
  tests/integration_conformance/test_system_runtime.py \
  tests/frameworks/test_provider_framework_matrix.py \
  --cov=agentic_systems.providers \
  --cov-config=.coveragerc-providers-branches \
  --cov-report=term-missing
python -m pytest -q --ignore=tests/release/test_tutorial_execution.py \
  --cov=agentic_systems.integrations \
  --cov-config=.coveragerc-frameworks-branches \
  --cov-report=term-missing
python -m pytest tests/providers -q --cov-config=.coveragerc-bedrock --cov=agentic_systems.providers.bedrock_runtime --cov=agentic_systems.providers.bedrock --cov-report=term-missing
python -m compileall -q src tests tutorials
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
```

The full pytest suite executes the 17 deterministic notebooks and statically
validates the 3 Provider notebooks. No separate undocumented notebook gate
should be substituted for this evidence.

## Bundle Hygiene

```text
[ ] No caches, notebook checkpoints, old distributions or egg-info directories are bundled.
[ ] No API keys, AWS credentials, local paths or notebook outputs with secrets are committed.
[ ] dist/ contains only artifacts rebuilt from the final source tree.
[ ] Wheel and sdist pass twine check and their hashes are recorded.
```

## Release Candidate

```text
[ ] Version agrees in pyproject, package, CLI, changelog and current release docs.
[ ] Public API count and Bedrock signatures match their frozen contracts.
[ ] Core coverage remains 100%; the Bedrock ratchet never decreases.
[ ] Ruff, pytest, Markdown quality and tutorial gates pass on Python 3.10 and 3.14 CI.
[ ] Wheel installs and the CLI/import smoke passes outside the repository.
[ ] The release is built from the reviewed clean commit/tag, not an earlier working tree.
[ ] GitHub release and PyPI publication occur only after the tag gates pass.
```

## Consumer Smoke

Validate the built wheel from an isolated environment, not the editable source:

```bash
python -m venv .tmp/wheel-smoke
.tmp/wheel-smoke/bin/python -m pip install dist/agentic_systems-*.whl
.tmp/wheel-smoke/bin/python -c "import agentic_systems as a; m=a.api_contract(); assert len(a.__all__) == 78; assert m['entry_count'] == 370; assert m['scenario_count'] == 10"
.tmp/wheel-smoke/bin/agentic-systems version
```

The equivalent Windows executables live under `.tmp/wheel-smoke/Scripts/`.
A release smoke must confirm version, CLI, 78 exports, 370 export/member IDs,
10 shared scenarios and lazy optional imports. Live Provider readiness is separate.
