# Mutation gate policy

Approved in the user review: execute every selected mutant and require zero unresolved survivors. Reviewed equivalent mutations are reported separately and never counted as killed.

## Verification

The workflow removes generated state, executes mutmut with pipefail, and only after a successful run records the gate receipt. The gate checks:

- Exact Python and mutmut versions and the source hashes of all three selected files.
- Exact selected module scope and mutation counts for each file.
- Every verdict: only killed verdicts and individually approved equivalent survivors are accepted. Pending, missing tests, timeout, suspicious and unexpected statuses fail.
- Each surviving diff's SHA256 against mutation-equivalents.json. The manifest retains the reviewed diff and proof, not just unstable mutant IDs.
- No duplicate or unused equivalence approval. An equivalent that disappears or becomes killed requires manifest review.
- A successful-run receipt bound to current source, tests, metadata, checker, pytest/mutmut configuration, workflow, versions and manifest. Missing or changed evidence fails.

The receipt certifies ordering in the trusted CI workflow; it is not a cryptographic attestation against a malicious person able to rewrite the workflow. Changes to the gate, workflow and equivalence manifest require the same code review as runtime changes.

The raw mutation report remains an artifact alongside mutation-gate.json and the approval manifest. The numeric acceptance threshold is zero unresolved cases; there is no general percentage or survivor-count allowance.

## Maintaining approvals

Do not regenerate approvals automatically from survivors. Inspect the exact diff, establish equivalence over the supported input domain, record its proof, verify the tool/Python versions and update source hashes and expected catalog counts only after a fresh complete run. A new surviving diff always requires a new review. Code or dependency upgrades invalidate the relevant evidence.

The six initial approvals concern ensure_ascii=False becoming None in Python's JSON encoder. Both select the same false branch; all other arguments remain identical. These approvals do not cover arbitrary False/None changes.

Previous batch documents retain historical mutation IDs; current approvals are solely the version/source/diff-bound records in mutation-equivalents.json.
