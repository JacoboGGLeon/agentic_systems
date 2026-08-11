# Checkpoint 1.1.3 — Documentation Architecture

Status: implemented and validated locally. This is a maintenance checkpoint after the published
1.1.2 release; it is not yet a package release or PyPI version.

## Objective

Make the documentation a single navigable system with explicit separation
between current product contracts, architectural decisions, historical evidence
and future proposals. No public API or runtime behavior is added.

## Scope

- consolidate duplicated conceptual and contract documents;
- correct stale Framework/Graph, migration and release narratives;
- replace per-step checkpoint files with durable historical summaries;
- index ADRs and RFCs;
- keep one current release-evidence document;
- make every retained document reachable from an intentional index.

## Compatibility

```text
public symbols: unchanged (111)
package version: unchanged while checkpoint is under review (1.1.2)
runtime behavior: unchanged
optional dependencies: unchanged
serialization contracts: unchanged
```

## Exit Gates

1. Markdown links and runnable snippets pass the release tests.
2. No retained current document teaches superseded behavior.
3. Historical files identify themselves as historical.
4. ADRs and RFCs are indexed.
5. Root README, install, tutorials and docs navigation agree.
6. Ruff and the relevant release/test suites remain green.
## Validation

```text
documentation Markdown files: 46 -> 26
orphaned retained documents: 0
retired parallel-source contract: pass
Markdown links and Python snippets: pass
focused documentation/release tests: 12 passed
full pytest: 382 passed
Ruff over src and tests: pass
public API/runtime source changes: 0
```
