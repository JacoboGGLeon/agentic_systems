# Agentic Systems 1.1 Release History

This file preserves evidence for the 1.1.0 release candidate, the promoted
1.1.0 release and the unpublished 1.1.1 maintenance checkpoint. It is not
current installation guidance.

## 1.1.0 Release Candidate And Promotion

`1.1.0rc1` was promoted to 1.1.0 on 2026-07-19 after automated gates and a
manual notebook matrix passed. Its claim was traceability—not literal identity—
across API, documentation, tutorials and tests.

Recorded evidence:

```text
pytest: 393 passed
coverage: 100.00% over 6,193 statements
notebooks: 18/18 executed, 0 failed
wheel and sdist: twine check passed
isolated wheel import and CLI: passed
```

Python Runtime was exercised locally. OpenAI, Bedrock and vLLM had controlled
conformance and failure evidence but no live account/model/GPU claim. LangGraph
had adapter evidence; OpenAI Agents-style and Strands remained non-SDK
identities.

The RC documents recorded different intermediate public-symbol totals while the
release tree stabilized. Those counts are historical build observations, not a
compatibility baseline; the current baseline is frozen by release contracts.

## Unpublished 1.1.1 Checkpoint

Version 1.1.1 was never tagged or uploaded to PyPI. Its maintenance work reduced
accidental packaging/test surface and was superseded by 1.1.2. It established
the split between deterministic notebook execution and static Provider-notebook
checks and preserved the 111-symbol public inventory.

## Current Evidence

See [Agentic Systems 1.1.2](../RELEASE_1_1_2.md) and the project changelog.
