# Agentic Systems Studio 2.1

Studio is one conversational Agentic System presented through two equivalent
entry points:

- `notebooks/00_conversational_system.ipynb` runs the system directly;
- `app.py` wraps that same system in a Streamlit chat application.

The application is intentionally small. A deterministic Python boundary creates
a bounded context envelope and records tool evidence. A reasoning Agent handles
language through the provider and framework selected by `.env`. Both boundaries
return the same normalized `RunResult` contract used by the library.

The reasoning Agent also receives one runtime Skill that grounds product
questions in the installed Agentic Systems 2.1 grammar. The Skill exposes a
deterministic public-API description and canonical code template, so a local
model does not have to guess what this project means by Tool, Skill, Agent,
System, Graph, Environment or Eval.

## Runtime portability

Reasoning providers:

- `python-runtime` (deterministic Hello World control; it is not an LM)
- `openai-runtime`
- `ollama-runtime`
- `bedrock-runtime` (API key or the normal boto3/IAM credential chain)
- `vllm-runtime`

`auto` is the optional runtime-selection mode. It chooses one configured
Provider before execution; it is not a fifth reasoning Provider and never means
that several Providers ran.

Frameworks:

- `native`
- `langgraph`
- `openai-agents`
- `strands`

There is no provider fallback inside Studio. If the selected runtime cannot run,
the chat shows the normalized failure and preserves the declared identity.

## Install in an isolated kernel

From the standalone `agentic-systems-studio-2.1.1.zip`, extract the archive,
enter its root and run:

```text
python -m venv .venv-studio
.venv-studio/Scripts/python -m pip install "agentic-systems==2.1.1"
.venv-studio/Scripts/python -m pip install -e ".[ui,notebook]"
```

The Studio package pins the same Agentic Systems version, so pip rejects a
mismatched runtime instead of silently mixing releases.

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

Use exactly one configuration file. The standalone Studio archive copies its root
`.env.example` to its root `.env`; the ADA delivery uses the single `.env.example`
at the ADA bundle root. Provider credentials remain in the managed environment and
are never written to Studio artifacts, attestations or bundles.

## Run

From the repository root, launch the application directly:

```text
python -m streamlit run examples/agentic_systems_studio/app.py
```

Open `notebooks/01_launch_studio.ipynb` and run both cells. The launcher binds
Streamlit to loopback, checks health and provides both the local URL and the
ADA/JupyterLab proxy URL.

Studio discovers the routes configured by the canonical `.env` and managed host
environment. The sidebar can select any discovered Provider and any installed
Framework for the current session; credentials are never entered, copied or
persisted by the UI. Edit `.env` and restart Studio only when the available
runtime contract itself changes. `python-runtime` remains visibly labeled as a
deterministic mock without a language model.

Every assistant turn renders two public observability lines below the natural
language answer. The processing mark reports the Provider, Framework and Tools
that actually ran. The usage mark projects every measurement supplied by the
runtime (requests, tokens, latency and scheduler data when available) and says
explicitly when a field was not reported; Studio never invents missing usage.

To exercise the same conversational system without the UI, run the live gate:

```text
python examples/agentic_systems_studio/scripts/validate_conversation_live.py \
  --providers python-runtime openai-runtime ollama-runtime bedrock-runtime \
  --output .tmp/studio-live.json
```

The report keeps both human answers, exact Tools, complete normalized usage and
full lineage. Passing requires semantic content and runtime identity, not only
`ok=true`. Provider credentials and models still come exclusively from `.env`
or the managed host.

## What the reference proves

- the same source runs with or without a UI;
- deterministic and reasoning boundaries remain separate;
- provider and framework are configuration, not application branches;
- conversation history is bounded before entering a model;
- arithmetic is established by a deterministic Tool;
- Agentic Systems code is grounded by a runtime Skill rather than model memory;
- reasoning metadata stays private while tool evidence remains observable;
- processing and usage are projected from the public `RunResult` API;
- every turn produces a serializable, invariant-checked `RunResult`;
- failures are visible and never trigger a silent provider fallback.
