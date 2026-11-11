# 2.1.7 candidate validation

This candidate removes CLI project generation and bundles the authoring skill. It is not published. SDK engine/runtime implementation is unchanged. SDK, Studio, ADA and active learning/skill version targets are 2.1.7. Historical reports and saved notebook outputs retain their original identities.

## Executed locally (Python 3.12.14)

- Full canonical source suite: **888 passed**, zero failures/skips, one existing runpy warning.
- Full canonical installed-wheel suite: **888 passed**, zero failures/skips, **100% statement coverage** (2027 statements) of the measured SDK surface; private engine excluded by the existing coverage configuration. Zero blocked application network/process attempts and zero inference.
- External installed skill smoke: 9 commands PASS, including existing-destination refusal, rejected `new` with no new project, ZIP integrity, first Tool and complete minimal composition.
- Wheel/source/installed bytes and 120 RECORD hashes verified. Wheel reconstructed from sdist matches SDK/skill payload. No scaffolder/templates/scaffold script in either payload. Final candidate Python payload matches the wheel used by the full suite.
- Strict Twine validation of wheel/sdist, Ruff, Pyright (zero errors), three import contracts, secret gate and catalog checks PASS.
- Current examples: **58 passed**, zero failed, one local-service example skipped. The stale creator example initially called removed `new`; it now demonstrates bundled skill distribution.
- Active documentation coherence: 62 pages and 33 notebook metadata/code assertions checked; reading views regenerated. Saved notebook execution outputs were preserved, not relabeled as 2.1.7 runs.

Raw logs, failures and summaries: [evidence](evidence/217/test-summary.json), [installed coverage](evidence/217/installed.log), [resource smoke](evidence/217/skill-distribution.json), [integrity](evidence/217/integrity-final.json), [payload checks](evidence/217/payload-checks.json).

Commands: `python scripts/test_offline_214.py --source` and `python scripts/test_offline_214.py -p pytest_cov --cov=agentic_systems --cov-report=term-missing`, each with a JUnit output path. Install the built wheel and optional Studio/ADA first, and set AGENTIC_VALIDATION_EVIDENCE when running `scripts/validate_skill_distribution.py`. That script runs the actual installed CLI from a temporary directory outside the checkout. Build with `scripts/build_candidate.py NEW_DIRECTORY`; verify using `scripts/verify_candidate.py WHEEL`.

## Failures retained and scope limits

The first local source run failed because this environment's SOCKS proxy required socksio. Installing that environment dependency fixed the failures without SDK changes. The initial notebook invocation omitted a required environment variable; after correction the kernel failed with `Operation not permitted`/ZMQ socket restrictions. Fresh-kernel notebook execution is **BLOCKED locally**, not PASS; its original CI step remains required. See [kernel log](evidence/217/notebooks-final.log).

Prior PR CI failed the installed coverage threshold because the editable-skill fallback was not exercised; a new test covers that real branch. Prior mutation CI failed baseline collection because canonical skill resources were absent from the copied workspace; `also_copy` now includes `skills`. These fixes do not certify a fresh mutation run. Python 3.10–3.14 CI and mutation checks on the final commit remain release gates, with no weakening or reinterpretation of historical equivalence approvals.

No live provider/service certification, publication, or 2.1.6 replacement occurred. The artifacts are local candidates; their build manifest refers to the pre-commit baseline plus the actual changed source fingerprints, not a sealed/promotable final commit. Final release artifacts must be built and tested by CI on the reviewed commit.
