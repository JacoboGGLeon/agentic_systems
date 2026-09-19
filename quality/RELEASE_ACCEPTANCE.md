# Release acceptance ledger

No release is certified by this file alone. Each mandatory row requires evidence.

| Release | Promise | Implementation/test | Evidence | Status |
|---|---|---|---|---|
| 2.1.2 | Parent actions survive child projection | lineage.py / test_lineage_ownership.py | Regression reproduced before fix; full suite on cbbfa14 passes | Offline verified |
| 2.1.2 | Compatible lineage across all boundaries | Existing API, contract and lineage suites | 1303 passed; 6 opt-in live notebook skips, not approvals | Offline verified; live pending |
| 2.1.2 | Agreed live matrix | Python, Ollama, OpenAI and Bedrock API key across supported frameworks | Fresh exact-wheel attestations required | Pending |
| 2.1.2 | Immutable distribution | RELEASE_PUBLISHING runbook | OIDC runs and remote hashes | Pending |
| 2.2 | In-process evidence memory | Preserved development branch | Unit/property tests and C01-C16 required | In development |
| 2.2 | Explicit context and integrated lineage | Preserved context implementation | SDK boundary receipts and episode E2E required | In development |
| 2.2 | Complete live matrix and publication | Same release gates as 2.1.2 | Fresh exact-wheel evidence | Pending |

Working copies are isolated. User-approved pilot: at most USD 5 AND 40 inference
requests, including judges and retries, on configured endpoints/models only.
Full certification requires a separate budget after the pilot. No paid calls
have been made for this candidate.

User deferred vLLM, Bedrock IAM and ADA until final 2.2 verification. These routes
are not certified by 2.1.2's revised acceptance scope. Historical attestations
do not certify these candidates.

Additional local verification on cbbfa14 (Python 3.14.2): 1278 core-branch tests
passed, 98.34% coverage against the unchanged 98.1% gate; 85 Studio tests passed.
Lint, strict typing, legacy typing ratchet (191 errors, no regressions), licenses,
secret scan, complexity and performance gates passed. The reused editable
environment requires PYTHONPATH pointing to this checkout's src; these checks
do not replace isolated wheel certification or Python 3.10-3.14 installation.
