# Agentic Systems 2.1.7

Bundled authoring skill and a smaller CLI.

The SDK wheel/sdist includes the canonical authoring skill. Use `skill info`,
`skill install [destination]` and `skill export file.zip` without network calls.
Install/export refuse existing paths. Importing into a remote assistant account
remains a manual step. Runtime `toolkit.skill` is unchanged.

Breaking CLI change: `new` and bundled project generation are removed. Use
repository examples, notebooks or skill assets as application starting points.
Existing generated projects are not deleted. Agent execution API is unchanged.

Current learning/skill metadata targets 2.1.7; recorded historical evidence retains
its original artifact identities. New live inference is not claimed. Publication
requires successful quality/mutation checks on final source, a sealed candidate
and reviewed TestPyPI-to-PyPI promotion; no 2.1.6 artifact may be replaced.
