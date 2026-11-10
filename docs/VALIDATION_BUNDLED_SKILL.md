# Bundled authoring skill: local acceptance

Date: 2026-11-10. Scope: additive CLI, packaging and authoring-skill documentation changes, on the 2.1.6 source baseline. These are unreleased local candidate bytes, not the published 2.1.6 artifact and not a sealed release. No published version was replaced.

The README shared by GitHub and package metadata now describes `skill install`, `skill export` and `skill info`, with explicit next-release availability. The canonical skill retains SDK 2.1.6 target instructions and fixed guards. Publishing the feature requires a new package version, aligned learning/skill metadata and the normal CI/promotion gates.

| Check | Actual outcome | Evidence |
| --- | --- | --- |
| Canonical selected contracts against installed wheel | 303 passed; zero failed/skipped; one existing runpy module-reimport warning | [log](evidence/bundled-skill/installed-tests.log), [JUnit](evidence/bundled-skill/installed-tests.xml) |
| Source tests for installer, CLI and graph boundaries | 29 passed; 100% statement coverage of `_skill_distribution.py` and `cli.py` | [coverage](evidence/bundled-skill/source-coverage.log) |
| Install/export and execute bundled first Tool/scaffolder from `/tmp`, outside checkout | PASS; imports assert site-packages | [smoke](evidence/bundled-skill/external-smoke.log) |
| Tests from the generated application | 2 passed | [log](evidence/bundled-skill/generated-tests.log) |
| Wheel build, source/installed bytes and RECORD verification | PASS; 136 RECORD hashes verified | [build](evidence/bundled-skill/build.log), [integrity](evidence/bundled-skill/integrity.json) |
| Wheel rebuilt from sdist | PASS; 131 SDK/resource payload files match | [rebuild](evidence/bundled-skill/sdist-rebuild.log), [parity](evidence/bundled-skill/sdist-parity.json) |
| PyPI metadata/README validation | `twine check --strict`: both wheel and sdist PASS | [log](evidence/bundled-skill/twine.log) |
| Focused Ruff checks | PASS | [log](evidence/bundled-skill/ruff.log) |
| Learning documentation coherence | 62 pages and 33 notebook metadata/assertions checked; notebooks not executed | [log](evidence/bundled-skill/learning-docs.log) |

Source and installed tests overlap; do not sum their counts as unique coverage. Coverage is statement coverage of two modules, not 100% SDK branch/feature coverage. The selected regression modules cover contracts, graph composition, Context/Memory, episode lifecycle, Evals, evidence/result integrity, resource loading and release safeguards. Some SDK adapter/server tests use offline fixtures or mocks.

The new tests verify complete resource identity, SDK-target coherence, default/custom destinations, paths with spaces, deterministic importable ZIPs, existing files/directories/broken symlinks, partial-write cleanup, missing bundles, bytecode exclusion, resource symlink rejection and bundled/source lookup. Existing user destinations are never overwritten.

## Reproduce

Build with `python scripts/build_candidate.py NEW_DIRECTORY`, install its wheel into a clean environment with pytest, and run tests with `-o pythonpath=` to avoid the repository's default source import. Set `AGENTIC_TEST_REQUIRE_INSTALLED=1` to enforce site-packages imports. The JUnit record lists the executed canonical test modules. `python scripts/verify_candidate.py PATH_TO_WHEEL` compares installed, source and RECORD bytes.

For a focused source check, run:

```bash
PYTHONPATH=src python -m pytest -o pythonpath= tests/current/test_skill_distribution.py tests/current/test_cli.py tests/current/test_graph_boundaries.py --cov=agentic_systems._skill_distribution --cov=agentic_systems.cli --cov-fail-under=100
```

The [candidate manifest](evidence/bundled-skill/candidate-manifest.json) records artifact hashes and source fingerprints. It was built before committing this proposal; its `commit` is the baseline, while `source_sha256` binds the actual tested modified files. This is local development evidence, not an authorization to promote these bytes as 2.1.6.

Not executed: full release CI matrix, complete mutation campaign, live provider/model/service calls, or publication. No behavior of the SDK's agent execution engine was changed.
