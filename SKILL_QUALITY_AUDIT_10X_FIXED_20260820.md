# Agentic Systems skill: fixed 10x quality audit

Date: 2026-08-20

This report supersedes the two earlier skill-audit reports.

## Verdict

The skill, scaffolder and generated applications now satisfy the local 1:1
contract for Source, manifest, runtime Skill, tests, notebook, Mermaid and
SQLite inventory.

Local confidence score: **94/100**.

The remaining six points represent live combinations that require their target
environments: Bedrock API-key/IAM, vLLM on the target GPU, and optional
framework adapters in live mode. Static construction for those combinations is
verified.

## Defects corrected

1. Generated `tools.py` now contains the deterministic domain tools declared by
   every stage instead of only `normalize_input` and `record_note`.
2. Manifest stage Tool identities and runtime Skill Tool identities resolve to
   the same decorated functions.
3. Generated applications include `settings.py`, `skills.py`, `agents.py` and
   `tests/test_execution.py`.
4. `python-runtime` is rejected as a reasoning provider while remaining the
   runtime for deterministic operator stages.
5. Manifests declare execution and provider/framework policies.
6. SQLite stores and validates the declared stages and Tool inventory.
7. Notebooks contain stable cell IDs and a portable `src` bootstrap, and execute
   deterministic checks from a fresh kernel before the live opt-in cell.
8. README files document installation, tests, CLI execution and notebook
   execution.
9. The scaffolder validates Tool contracts, runtime Skill contracts, SQLite,
   notebooks and documentation instead of accepting syntax alone.
10. The official skill helper emits JSON and returns a failing exit code when
    validation is not green.

## Final evidence

| Gate | Result |
|---|---:|
| Fresh scaffolds generated | 10/10 |
| Scaffolder contract checks | 130/130 |
| Manifest Tool contracts resolve | 10/10 |
| Runtime Skill Tool contracts resolve | 10/10 |
| Generated pytest tests | 67 passed |
| Generated live tests without opt-in | 10 correctly skipped |
| Fresh-kernel notebooks | 10/10 |
| Static Provider × Framework matrix | 160/160 |
| OpenAI/native live | 10/10 |
| Ollama/native live | 10/10 |
| Agentic Systems Studio suite | 31 passed |
| Final repository suite | 938 passed, 6 skipped |
| Ruff lint | passed |
| Ruff format check | passed |
| Canonical skill quick validation | passed |
| Installed skill quick validation | passed |
| Canonical ↔ installed hash differences | 0 |

## Live providers

### OpenAI

- provider: `openai-runtime`
- framework: `agentic-systems`
- model: `gpt-4.1-mini`
- passed: 10
- failed: 0
- summed latency: 106.38 seconds
- prompt tokens: 13,308
- completion tokens: 2,278

### Ollama

- provider: `ollama-runtime`
- framework: `agentic-systems`
- model: `qwen3:4b-instruct`
- passed: 10
- failed: 0
- summed latency: 81.73 seconds
- prompt tokens: 11,698
- completion tokens: 1,745

## Static matrix

All ten generated systems built and inspected for all 16 combinations of:

- providers: OpenAI, Ollama, Bedrock and vLLM;
- frameworks: native Agentic Systems, LangGraph, OpenAI Agents and Strands.

This is 160/160 static combinations. It is not a claim that the 160
combinations have all been live-verified.

## Bundle

The final Studio bundle contains ten regenerated nested system bundles.

- file: `examples/agentic_systems_studio/dist/agentic-systems-studio-2.0.zip`
- SHA-256: `7dd0dc1ea1202d5382734776aab0db4513facc5be17900414ac1d2901e3451b5`

## Remaining sandbox work

Before making a universal live-matrix claim:

1. run Bedrock with the API-key path;
2. run Bedrock with the ADA IAM-role path;
3. run vLLM in Colab or the target GPU sandbox;
4. live-test the optional framework adapters on the combinations the release
   will explicitly advertise.
