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
