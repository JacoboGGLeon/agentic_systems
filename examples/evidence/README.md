# Evidence policy

Catalog entries distinguish the following evidence kinds through their linked sources:

- Published release acceptance: immutable GitHub assets tied to the exact wheel,
  commit and acceptance profile. The 2.1.2 wheel SHA-256 is
  `2c14a8e6f871fcc455acbf899db851130c49a129ba988821d6656e90ebc3d47b`.
- Historical raw record: the existing Studio Ollama evidence, with its original
  date, model and framework identity. It does not identify the published 2.1.2 wheel.
- Summary extract: the protocol challenge and API sandbox summaries in this
  directory preserve selected facts and the SHA-256 of their original local JSON.
  Original raw artifacts were not copied into this catalog. These summaries do
  not recreate a signed attestation or prove unrecorded behavior.
- Documentation report: existing experiment reports preserve route counts,
  failures, manual review limits and external artifact locations. If those raw
  artifacts are outside the checkout, a report does not pretend to include them.
- Design: a planned experiment is never reported as executed.

No credentials, environment files, private datasets or full raw provider responses
are added here. Historical and current budget ledgers remain separate from the
catalog. Updating these pages does not authorize a request or reset any budget.

A passing deterministic check is not a semantic pass; a matched binary verdict
does not establish faithful explanations or citations. A pass belongs to the
reported source/artifact, model, provider, framework, environment and cases only.
