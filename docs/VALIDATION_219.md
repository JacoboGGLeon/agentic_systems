# Validation scope · Agentic Systems 2.1.9

Published on 2026-11-12. The [GitHub release](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.9) and [PyPI distribution](https://pypi.org/project/agentic-systems/2.1.9/) identify the delivered artifact. Acceptance is offline maintenance acceptance; no new live model inference is claimed.

| Evidence | Observed scope |
|---|---|
| [Exact-commit quality](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/43151457496) | PASS: Python 3.10–3.14; 895 source and 895 installed-wheel tests per version; 35 notebooks checked in fresh kernels per version under the offline profile; live/service cells skipped or disabled |
| [Mutation](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/43151457533) | PASS: 2,366 total; 2,360 killed; 6 reviewed equivalents; 0 unresolved |
| [Candidate sealing](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/43152374008) | PASS: exact quality-built bytes; 106 packaged Python files checked against the reviewed policy |
| [TestPyPI promotion](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/43152611705) | PASS on attempt 2; published hashes and downloaded-wheel installation verified |
| [PyPI promotion and GitHub finalization](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/43153268725) | PASS on attempt 3; published hashes, Python 3.10/3.14 installation and immutable release assets verified |
| 2.1.9 live-model acceptance | NOT RUN on this artifact; historical runs are not relabeled |
| Historical Native / OpenAI Agents real-data success | SDK 2.1.8; original JSON and recorded-output viewer retained |
| Historical failed Native PDF rerun | Separate failed execution retained alongside the successful baseline |

Release commit: `eab28d08bf89eec20d90a4212ae7cae116585f58` (tag `v2.1.9`).

Wheel SHA-256: `c0e8f7046dd4a839225f2673de8d5cceecef7d8ba7cecbc00bd706fa5311c233`.

[Release manifest](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.9/release-manifest.json) SHA-256: `20ac1f9b9291395dda3ab98f63a2d29c3f2505109c8303907a3a9eacd63607d9`.

Initial publication checks timed out while registry metadata propagated. The first PyPI installation checks also ran before the pip index exposed the version. Those failed attempts remain in the workflow history. Retries resumed the same candidate and hashes without rebuilding or replacing published files.

See the [acceptance policy](../release/policy-2.1.9.json), [preparation review](DOCUMENTATION_REVIEW_219.md) and [migration](MIGRATION_218_TO_219.md). The expanded policy/contract provider-framework matrix remains 2.1.10 work. Memory and continuations are process-local; EMR and distributed Spark remain unverified.
