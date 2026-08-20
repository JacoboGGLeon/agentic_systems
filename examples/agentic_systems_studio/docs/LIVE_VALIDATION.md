# Live validation evidence

Date: 2026-08-20

These checks ran from the repository workspace with real provider calls. No
credential values, prompts containing secrets, or provider responses are stored
in this document or in the distributable bundle.

## Provider and framework matrix

The same data-quality system and natural-language CSV prompt were used in every
row. Each successful hierarchical RunResult had two children: one deterministic
python-runtime operator and one language-model reasoner.

| Provider | Framework | Result | Seconds | Child engines |
| --- | --- | ---: | ---: | --- |
| openai-runtime | native | pass | 8.07 | python-runtime, openai-runtime |
| openai-runtime | langgraph | pass | 5.46 | python-runtime, openai-runtime |
| openai-runtime | openai-agents | pass | 8.42 | python-runtime, openai-runtime |
| openai-runtime | strands | pass | 7.60 | python-runtime, openai-runtime |
| ollama-runtime | native | pass | 4.47 | python-runtime, ollama-runtime |
| ollama-runtime | langgraph | pass | 2.51 | python-runtime, ollama-runtime |
| ollama-runtime | openai-agents | pass | 3.12 | python-runtime, ollama-runtime |
| ollama-runtime | strands | pass | 3.20 | python-runtime, ollama-runtime |

OpenAI used the configured project model. Ollama used qwen3:4b-instruct, a Q4
instruction-tuned model, on the local NVIDIA RTX 3070 Laptop GPU.

## Agentic Systems Creator

The five-stage creator was run with the same industrial application request.

| Provider | Result | Seconds | Children | Tool events |
| --- | ---: | ---: | ---: | ---: |
| openai-runtime | pass | 33.44 | 5 | 6 |
| ollama-runtime | pass | 9.80 | 5 | 3 |

Each run contained one deterministic python-runtime child followed by four
reasoning or review children on the selected provider.

## Regressions closed during validation

- Empty model completions are structured failures with error code
  empty_model_output; they are no longer reported as successful runs.
- The data-quality operator extracts CSV from natural-language instructions and
  fenced Markdown before profiling it deterministically.
- CLI notebook generation preserves existing Rich outputs by stable cell ID.
- All 21 CLI notebooks were executed from fresh kernels and saved with outputs.

## Studio launchers

Both launch surfaces call the same public server API.

- agentic-studio serve started Streamlit on 127.0.0.1:8765, returned health
  status ok, recorded its PID and log, and printed the Jupyter proxy URL.
- jupyter-server-proxy 4.5.0 was tested with an authenticated Jupyter Server:
  /proxy/8765/_stcore/health returned HTTP 200 and body ok while both services
  were bound exclusively to loopback.
- notebooks/02_launch_studio.ipynb executed from a fresh kernel, returned health
  status ok, saved a real HTML button output for the proxy URL, and stopped its
  validation server cleanly.
- The server binds only to loopback and keeps Streamlit CORS and XSRF defaults;
  it does not copy the broader 0.0.0.0 configuration from the legacy notebook.

## Remaining external release gates

- Bedrock must still be repeated inside the ADA IAM sandbox after AWS enables
  the requested account quota. API-key and IAM paths remain separate tests.
- vLLM must still be repeated in the user's GPU/Colab target.

Those two gates do not invalidate the OpenAI/Ollama evidence above, but they are
required before claiming the complete multi-provider release candidate is zero.

## Complete ten-system Ollama gate

All ten catalog systems were executed with ollama-runtime, the native
agentic-systems framework and qwen3:4b-instruct after fixing provider tool
event identity. The result was 10/10 systems, 34/34 stages, 26 tool events,
13,593 total tokens, zero errors and 10/10 hierarchical RunResult invariant
checks passing. The credential-free machine-readable evidence is stored in
evidence/ollama-native.json.

OpenAI-compatible provider tool events now receive globally unique execution
IDs. The provider's original tool-call ID remains in
meta.provider_tool_call_id, preserving correlation without violating
hierarchical result invariants when the same tool is called more than once.

## Reproduce the external gates

Run scripts/validate_sandbox.py in ADA and Colab. Exact IAM, Bedrock API-key
and vLLM commands plus the 40-system-execution passing contract are documented
in docs/SANDBOX_VALIDATION.md.