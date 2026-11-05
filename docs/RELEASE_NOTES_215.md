# Agentic Systems 2.1.5

Maintenance release preserving the 2.1.4 public construction and execution API.

- Expand behavioral contracts and simplify redundant normalization and presentation logic.
- Require zero unresolved mutations, with six individually reviewed equivalent JSON-encoding changes reported separately. Every selected mutant still executes.
- Provide English narrative, captions and reading guides for 33 active notebooks, plus validated Markdown alternatives and Python language metadata.
- Correct PyPI README links and add explicit documentation/tutorial URLs.
- Refresh the SDK, skill and optional Studio/ADA distribution versions together.

Release acceptance requires successful quality checks on all five supported Python versions and the strict mutation workflow for the exact main commit. Candidate bytes come from that quality run and are sealed without rebuilding, promoted through TestPyPI, and reconciled by SHA256 before and after production upload.

The reviewed runtime source is pinned to commit 63a8b1d16271982d4ae489a9aecf5dd8cba14125; only the SDK release/version labels may differ in the executable payload. This is not an assertion that the runtime is byte-identical to the previously published 2.1.4 package.

No new live model calls are claimed. Historical provider results retain their original artifact identities. Bedrock/Qwen required nullable-field omission remains a fail-closed limitation; GPU, AWS IAM and ADA IAM environments remain separately unverified.
