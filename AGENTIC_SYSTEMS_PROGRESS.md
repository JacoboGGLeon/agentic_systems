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
import agentic_systems as lab
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
pytest: 210 passed
compileall: OK
wheel smoke: OK
PUBLIC_API: 101 names, 101 unique, no missing names
```
