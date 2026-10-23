# Provider Framework Conformance — API 2.1.3

Separate provider/framework identities with actual Python Runtime operators and configured-only external routes.

API/version scope: **2.1.3**.

## Input → process → output

Explicit provider/framework → deterministic operator → asserted result; external declarations remain not-run.

## Implementation

One canonical example.py; no alternative SDK constructors.

Readiness: **runnable with the exact 2.1.3 candidate; offline validation passed**.

- [Canonical implementation](../../../examples/provider_framework_conformance/example.py)
- [Walkthrough](../../../examples/provider_framework_conformance/README.md)

## Actual validation

Status: **offline-only**.

Four actual framework Python operators. External providers configured only; no inference.

- [Measured offline report](../../../revisions/2.1.3/implementation-evidence/REPORT.md)
- [Exact artifact and evidence hashes](../../../revisions/2.1.3/implementation-evidence/manifest.json)

## Limits and next action

Use exact artifact evidence; external routes need separate execution authorization.

This catalog update executed no inference. A historical or source-only result
does not certify another wheel, model, framework or environment.
