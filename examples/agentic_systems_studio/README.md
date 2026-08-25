# Agentic Systems Studio 2.1

Studio is one conversational Agentic System presented through two equivalent
entry points:

- `notebooks/00_conversational_system.ipynb` runs the system directly;
- `app.py` wraps that same system in a Streamlit chat application.

The application is intentionally small. A deterministic Python boundary creates
a bounded context envelope and records tool evidence. A reasoning Agent handles
language through the provider and framework selected by `.env`. Both boundaries
return the same normalized `RunResult` contract used by the library.

## Runtime portability

Reasoning providers:

- `openai-runtime`
- `ollama-runtime`
- `bedrock-runtime` (API key or the normal boto3/IAM credential chain)
- `vllm-runtime`
- `auto`

Frameworks:

- `native`
- `langgraph`
- `openai-agents`
- `strands`

There is no provider fallback inside Studio. If the selected runtime cannot run,
the chat shows the normalized failure and preserves the declared identity.

## Install in an isolated kernel

For local development:

```text
python -m venv .venv-studio
.venv-studio/Scripts/python -m pip install -e .
.venv-studio/Scripts/python -m pip install -e examples/agentic_systems_studio[ui,notebook]
```

On Linux, macOS, SageMaker or ADA, use `.venv-studio/bin/python` instead. In an
environment with restricted Internet, point pip at the approved Artifactory
through `PIP_INDEX_URL` and `PIP_TRUSTED_HOST`; the application never embeds
repository or registry credentials.

Copy `.env.example` to `.env` and choose the runtime contract there. Provider
credentials remain in the environment and are never written to Studio artifacts,
attestations or bundles.

## Run

Open `notebooks/01_launch_studio.ipynb` and run both cells. The launcher binds
Streamlit to loopback, checks health and provides both the local URL and the
ADA/JupyterLab proxy URL.

The Streamlit sidebar shows the provider, framework, model and limits loaded from
`.env`. Runtime configuration is deliberately read-only in the UI: change `.env`
and restart Studio when you want another provider or framework.

## What the reference proves

- the same source runs with or without a UI;
- deterministic and reasoning boundaries remain separate;
- provider and framework are configuration, not application branches;
- conversation history is bounded before entering a model;
- arithmetic is established by a deterministic Tool;
- reasoning metadata stays private while tool evidence remains observable;
- every turn produces a serializable, invariant-checked `RunResult`;
- failures are visible and never trigger a silent provider fallback.
