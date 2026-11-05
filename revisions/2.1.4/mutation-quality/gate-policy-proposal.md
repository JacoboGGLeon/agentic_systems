> Historical proposal. The user approved this direction; implemented policy is documented in gate-policy.md.

# Gate closure proposal — not applied

The gate still rejects every survivor. No workflow rule or mutation exclusion has been changed.

Redundant normalization, overwritten temporary values, and inactive lower bounds have been simplified in runtime code. These changes preserve the existing test contracts, including child.to_dict() dispatch, and retain coverage selection and all acceptance thresholds.

The residual equivalence class is json.dumps(..., ensure_ascii=False) becoming ensure_ascii=None: both select the same non-ASCII-escaping branch. Valid behavioral tests cannot distinguish them. Rewriting boolean constants or depending on argument-spelling assertions only to evade this operator would not strengthen behavioral verification.

A possible policy change, requiring explicit user acceptance because the original requirement prohibits exclusions or reduced criteria:

1. Continue generating and executing every mutant.
2. Require every non-equivalent mutant to be killed. No percentage allowance.
3. Permit only individually reviewed equivalent changes identified by exact normalized diff, enclosing function source hash, Python/mutmut versions and written equivalence proof. Numeric mutant IDs alone are insufficient.
4. Fail for any new survivor, stale or unmatched approval, missing test, timeout, suspicious result, incomplete run or baseline failure.
5. Report raw totals and reviewed equivalents separately; never count equivalents as killed.

This document proposes the decision boundary only. The equivalent-aware gate has not been implemented or enabled. The current strict gate remains failing until a policy is accepted or the mutation operator's supported equivalent cases are addressed upstream.

Previous equivalence documents and the 98-case audit describe the pre-refactor review snapshot; numeric IDs and exact diffs must not be reused as approvals for current source.
