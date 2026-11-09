# Agentic Systems 2.1.6

Maintenance release for learning materials and scaffolding. Public API and runtime
behavior are unchanged. Generated project notebooks now use English narrative.

The release includes a Tool-first starting path, current API/CLI and actor-contract
guides, executable example instructions, regenerated notebook reading views and
updated assistant guidance. See [the narrative review](NARRATIVE_REVIEW_215.md).

The included [integration report](VALIDATION_215_20261108.md) describes tests on
the unchanged 2.1.5 artifact: Bedrock IAM, vLLM Instruct/Thinking in Colab and
SageMaker, and fresh-kernel learning checks with local MCP/A2A. Those results
are historical evidence, not new live certification of 2.1.6. ADA's supplied
live log retains its stated artifact-identity limitation.

Release acceptance requires quality on Python 3.10–3.14 and the complete mutation
gate on the exact release commit. Quality-built bytes must be sealed, reviewed,
published and verified on TestPyPI before the same bytes reach PyPI.

Known limitation: Bedrock/Qwen may omit a required nullable Tool field; the
contract rejects this rather than supplying a default. This release does not
change provider behavior or claim arbitrary-prompt reliability.
