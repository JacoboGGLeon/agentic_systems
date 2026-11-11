# 2.1.7 candidate validation

This report records pre-publication candidate validation: removal of CLI project generation and bundling of the authoring skill. SDK engine/runtime implementation is unchanged. SDK, Studio, ADA and active learning/skill version targets are 2.1.7. Historical reports and saved notebook outputs retain their original identities.

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

Prior PR CI failed the installed coverage threshold because the editable-skill fallback was not exercised; a new test covers that real branch. Prior mutation CI failed baseline collection because canonical skill resources were absent from the copied workspace; `also_copy` now includes `skills`. The subsequent quality run [42957145873](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/42957145873) and mutation run [42957145881](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/42957145881) both completed successfully for reviewed head `5357691f4337a3321eed23f30085f4de5f8a4a43`. These results are not attributed to later documentation commits. Quality and mutation on the exact final main commit remain release gates, with no weakening of historical equivalence approvals.

The local offline campaign above did not invoke providers. Subsequent operator-supplied reports establish targeted live Bedrock acceptance for the frozen CI wheel in Studio and Processing; see [AWS acceptance](AWS_SESSION_VALIDATION_217.md). This does not certify all providers or EMR. The original local build and its pre-commit source fingerprints remain historical candidate evidence. The tested CI wheel has its own SHA and synthetic merge checkout, recorded separately. No publication or 2.1.6 replacement occurred. Final release artifacts still require exact-main CI, sealing and TestPyPI promotion. Documentation changes do not retrospectively change the identity of a tested wheel.


## Supplemental pipeline acceptance

Operator-supplied controller/comparison reports now mark both session variants PASS:
`automatic` campaign `20261111T055851Z-e0a39fd5` and `injected` campaign
`20261111T060123Z-33897585`. Four Processing jobs completed, with eight agent
executions and eight HTTP reservations according to the controller checks. Both
variants used the same runtime JSON; artifact continuity, worker session policies,
application lineage and dependency order passed. See the AWS acceptance document
and machine-readable summary for provenance and limits. EMR remains unverified.
