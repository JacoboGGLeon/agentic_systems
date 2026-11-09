# Documentation and learning review · 2026-11-08

## Source and artifact

Review started from main f14663041677eb39a6fc57cb9c4bb0152fd769eb and the
subsequent integration-documentation PR. Runtime API target is 2.1.5. Offline
example execution used the unchanged 2.1.5 wheel SHA256
`0003008de9cff10e3caa0c8e50a7a1c8beae3e73c9fe2ada59a2035887e00e84`.
Documentation, Skill instructions and scaffolder narrative are later edits;
this review does not relabel published artifacts or change the public API.

## Verified behavior

- All 15 documented public constructor/factory signatures matched runtime inspection.
- CLI help, version, api, doctor and new-project generation executed successfully.
- The generated quote and refund applications executed; both generated business tests passed.
- The Skill's complete offline composition example executed successfully.
- The repository example validator selected 59 entrypoints: 58 passed, one
  Strands MCP/A2A case requires its separate local-service profile. There were
  zero application networking/process attempts and zero inference requests.
- All 33 active notebooks passed their non-live/non-local-service code cells
  in separate Python processes, preserving cell order and top-level await.
  Optional actor dependencies and the ADA source package were present.
  The initial check failed on proxy configuration, a missing optional package,
  and the first harness's handling of top-level await; the corrected offline
  harness passed without changing notebook business code.
- Fresh Jupyter-kernel execution was unavailable in this environment because
  its ZeroMQ transport was blocked. The cell checks are not a fresh-kernel
  notebook-rendering certification.
- An independent task using the revised Skill produced a beginner order
  classifier with batch Environment and Eval. Four batch records, three Eval
  cases and five strict-input rejection cases passed. A wrong expected answer
  failed as required. Result invariants and JSON lineage passed. No inference
  or application networking/process operation occurred. An import-time urllib3
  IPv6 probe was blocked by the test gate and recorded separately.

The independent task checks one realistic generation path. It does not establish
that all prompts produce correct applications or replace review of generated code.
Raw local review logs are retained separately, not published here as a new release
certificate. The operator-executed live campaigns have their own
[report and artifact hashes](VALIDATION_215_20261108.md).

## Final local checks of the revision

The canonical source suite passed 873 tests with zero blocked application
network/process attempts and zero inference requests. One existing runpy warning
was reported. The initial full-suite collection required the optional Studio UI
dependency; inherited SOCKS proxy settings also caused SDK-client setup failures
until removed from this strictly offline test process. No assertions were weakened.

A private review wheel was built and installed in a separate virtual environment.
From outside the repository, version/new, quote, app.py and both generated tests
passed. The generated notebook narrative is English. This review wheel is a local
candidate and was not uploaded or substituted for the published 2.1.5 wheel.

Notebook schema/reading-view checks pass for all 33 notebooks. Catalog checking
passes for 52 entries; the new learning-navigation check covers 62 pages and the
33 target-version metadata records. These checks now run in quality CI.

## Editorial decisions

Start with one useful result, then introduce each abstraction when needed. Keep
input, operation, expected output and a negative control visible. Give a working
directory and executable command. Explain business rejection separately from
runtime failure. Keep actor selection, Tool requirements and finalization distinct.

Catalog target API is current; validation version/hash and earlier catalog text
retain historical identity. Active notebook metadata identifies its target SDK
separately from retained historical metadata and saved execution output.
Do not infer a new model run from an editorial version label.

## Maintenance boundaries

Generate notebook Markdown views from their source notebooks. Update current
landing pages and stable links without overwriting campaign evidence. Older
migration/generation scripts outside the current quality workflow can refer to
retired APIs (for example generate_api_contract.py and
 audit_generated_skill_static_matrix.py); treat them as historical tooling, not
commands for current learners. They were not used to generate this review.

The published PyPI 2.1.5 description remains tied to its uploaded artifact. A
future documentation-bearing release needs its own build, quality and promotion
checks. No model/provider campaign was rerun for this editorial work.
