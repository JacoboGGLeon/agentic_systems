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
its original artifact identities. Targeted operator-reported Bedrock acceptance
passed against the frozen 2.1.7 wheel in SageMaker Studio and an isolated Processing
job: direct Boto3, supplied-session Agent, Studio default-chain Agent, JSON transfer,
RunResult invariants and lineage. This is not blanket provider/framework certification.
See [AWS evidence and limits](AWS_SESSION_VALIDATION_217.md). EMR, Spark executors
and long-running credential renewal remain unverified. Both new SageMaker two-step
pipelines passed according to operator-supplied controller/comparison reports;
automatic and supplied-session modes used identical runtime JSON.

2.1.7 remains unpublished. Publication requires successful quality/mutation checks on final source, a sealed candidate
and reviewed TestPyPI-to-PyPI promotion; no 2.1.6 artifact may be replaced.
