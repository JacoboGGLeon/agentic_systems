# Agentic Systems 1.1 Release Candidate

Candidate version: `1.1.0rc1`, promoted to `1.1.0` on 2026-07-19.

Status: historical candidate record; promotion gates passed.

## Coherence Claim

**Agentic Systems 1.1 establishes verifiable coherence between its API,
documentation, tutorials, and tests.**

```text
API == Docs == Tutorials == Pytests
```

This is a traceability claim, not literal identity. The release gates verify that
public concepts are defined in the API, explained in documentation, taught in the
canonical tutorials, and enforced by tests.

## Evidence Levels

| Surface | Evidence in this repository | Not claimed |
|---|---|---|
| `python-runtime` | Local deterministic execution and shared conformance tests | Equivalence with LM output |
| `openai-runtime` | Contract tests with controlled clients and failure paths | Live OpenAI account/model execution |
| `bedrock-runtime` | Contract tests with controlled clients and failure paths | Live AWS account/model execution |
| `vllm-runtime` | OpenAI-compatible client, config, and conformance tests | Live GPU server/model execution |
| `provider="auto"` | Environment-resolution and observability tests | Credential or endpoint availability |
| LangGraph | Boundary/projection tests and optional dependency behavior | Any deployed Graph application |
| OpenAI Agents-style | Style-only profile and metadata preservation | OpenAI Agents SDK adapter |
| Strands | Declarative-only profile and metadata preservation | Strands SDK adapter |
| Tutorials | JSON validation, public-import policy, clean outputs, code-cell compilation | Full cell execution in every target environment |

## Automated Gates

- public API inventory equals documentation;
- package and CLI versions agree;
- all canonical notebooks parse and compile;
- notebooks use the public `toolkit` import;
- notebooks contain no persisted outputs;
- Provider/Framework claims match conformance profiles;
- full pytest suite reaches the configured coverage threshold;
- wheel and sdist include only intended package and release metadata;
- wheel installs and imports in an isolated environment.

## Manual Notebook Gate

Run notebooks from a clean kernel in the order documented by
`tutorials/README.md`.

Record for each notebook:

```text
notebook
environment
provider selected
result: pass | explicit skip | fail
external service used
notes
```

An explicit skip is acceptable only for a documented optional external
dependency or missing credential. A skip must not be reported as successful
Provider or Framework execution.

## Promotion Rule

Promote `1.1.0rc1` only after:

1. automated gates pass on candidate artifacts;
2. the manual notebook matrix is recorded;
3. live Provider claims are backed by corresponding run evidence;
4. changelog and version are unchanged from tested artifacts;
5. the release commit is tagged intentionally.


## Recorded Automated Results

```text
pytest: 393 passed
coverage: 100.00% (6193 statements, 0 missing)
canonical notebooks: 18/18 executed, 0 failed
PUBLIC_API: 110 symbols
wheel: 57 entries, clean, isolated import passed
sdist: 74 entries, clean
twine check: passed for wheel and sdist
```
