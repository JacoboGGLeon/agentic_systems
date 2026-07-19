# Contributing Checklist

Use this checklist before handing off changes.

## API

```text
[ ] New public names are added to `agentic_systems.api`.
[ ] Recommended names are documented in `docs/API.md`.
[ ] Advanced names are documented as advanced, not as first-step API.
[ ] No tutorial imports from internal modules when `import agentic_systems as toolkit` works.
[ ] Optional dependencies are not required at package import time.
```

## Code Placement

```text
[ ] Provider-agnostic primitives live in core.
[ ] Backend/model execution lives in providers.
[ ] Framework adaptation lives in integrations.
[ ] Business/tutorial assets live outside src/agentic_systems.
[ ] CLI changes stay diagnostic and package-oriented.
```

## Docs

```text
[ ] README, docs and tutorials describe the same API names.
[ ] Docs include runnable minimal examples.
[ ] Docs explain return values and failure behavior.
[ ] Docs do not promote removed compatibility paths.
[ ] Notebook order in docs matches tutorials/.
```

## Validation

```bash
python -m pytest -q
python -m compileall -q src tests tutorials
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
```

## Bundle Hygiene

```text
[ ] No `__pycache__`, `.pytest_cache`, `.ipynb_checkpoints`, build artifacts, wheels or egg-info directories are bundled.
[ ] No API keys, AWS credentials, local sandbox paths or notebook outputs with secrets are committed.
[ ] Generated artifacts are either ignored or intentionally documented.
```

## Release Candidate

```text
[ ] Version agrees in pyproject, package, CLI, changelog, and RC docs.
[ ] Canonical notebooks parse, compile, use the public import, and have no outputs.
[ ] Provider/Framework support statements identify their evidence level.
[ ] Wheel and sdist content are inspected.
[ ] Wheel installs and imports outside the repository.
[ ] twine check passes.
[ ] Manual notebook matrix is recorded before final promotion.
```
