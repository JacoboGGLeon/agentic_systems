# Contributing Checklist

Use this checklist before handing off changes. The documentation map defines the
current sources of truth; historical checkpoints do not override them.

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
python -m pytest tests/providers -q --cov-config=.coveragerc-bedrock --cov=agentic_systems.providers.bedrock_runtime --cov=agentic_systems.providers.bedrock --cov-report=term-missing
python -m compileall -q src tests tutorials
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
```

The full pytest suite executes the 13 deterministic notebooks and statically
validates the 5 provider notebooks. No separate undocumented notebook gate
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
