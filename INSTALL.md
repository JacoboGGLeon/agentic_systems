# Install

Agentic Systems is published on PyPI as `agentic-systems`. PyPI installs the
library and CLI; executable notebooks live in the GitHub repository.

## Core Package

```bash
python -m pip install -U pip
python -m pip install agentic-systems
```

The core install includes the public API, CLI, deterministic Python runtime,
tools, skills, agents, systems, graphs, environments, evals, contracts, lineage
memory and human-readable results. It does not import or install optional
provider/framework SDKs.

## Optional Extras

Install only the boundaries you use:

```bash
python -m pip install "agentic-systems[openai]"
python -m pip install "agentic-systems[openai-agents]"
python -m pip install "agentic-systems[bedrock]"
python -m pip install "agentic-systems[langgraph]"
python -m pip install "agentic-systems[strands]"
python -m pip install "agentic-systems[vllm-client]"
python -m pip install "agentic-systems[vllm-server]"  # GPU/Linux host only
python -m pip install "agentic-systems[dev]"
```

| Extra | Purpose |
|---|---|
| `openai` | OpenAI provider and existing OpenAI-compatible endpoints. |
| `openai-agents` | OpenAI Agents SDK; installed package is `openai-agents`, import name is `agents`. |
| `bedrock` | boto3/botocore support for Bedrock SigV4 or native API key authentication. |
| `langgraph` | Native LangGraph orchestration adapter. |
| `strands` | AWS Strands Agents and MCP support. |
| `vllm` / `vllm-client` | Lightweight OpenAI-compatible client for an existing vLLM endpoint. |
| `vllm-server` | vLLM GPU/server stack; supported GPU/Linux hosts only. |
| `dev` | Test, coverage, lint and notebook tooling for this repository. |

The `all` extra installs the portable Provider/Framework SDKs and development
gates, but deliberately excludes the platform-specific vLLM GPU server. Install
`vllm-server` only on the machine that serves the model. Agentic Systems never
starts it implicitly; process ownership begins only at `server.start()`.

To connect to an already running vLLM endpoint, the lighter OpenAI extra is
sufficient:

```bash
python -m pip install "agentic-systems[openai]"
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_MODEL="your-model"
export VLLM_API_KEY="EMPTY"
```

## Stable Version

Pin the maintenance release when reproducibility matters:

```bash
python -m pip install "agentic-systems==2.1.0"
```

## From GitHub

Use this only when you intentionally want the current `main` branch rather than
the published PyPI release:

```bash
python -m pip install git+https://github.com/JacoboGGLeon/agentic_systems.git
```

## Local Development

From a cloned repository, install the same non-vLLM boundaries used by release
CI:

```bash
python -m pip install -U pip
python -m pip install -e ".[dev,bedrock,langgraph,openai,openai-agents,strands]"
```

Install `.[vllm-server]` separately only on a host that will actually run vLLM.

## Smoke Test

```bash
python - <<'PY'
import agentic_systems as toolkit

print("agentic_systems", toolkit.__version__)
print(callable(toolkit.tool), callable(toolkit.agent), callable(toolkit.runtime))
PY

agentic-systems doctor
```

## Deterministic Runtime Check

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

runtime = toolkit.runtime(
    provider="python-runtime",
    scheduler=toolkit.scheduler(timeout_s=5, max_retries=0),
)
agent = toolkit.agent(name="calc", tools=[add], runtime=runtime)
result = agent.run({"tool": "add", "input": {"a": 1, "b": 2}}, mode="eval")
assert result.ok and result.data["result"] == 3
```

## Tutorials

Tutorials are repository content and are not included in the wheel. Clone the
repository, install the development/provider extras you need and start Jupyter:

```bash
python -m pip install -e ".[dev,openai,bedrock,langgraph]"
python -m jupyter lab tutorials
```

Continue with [First Run Onboarding](docs/ONBOARDING_FIRST_RUN.md).

## Build From Source

Build only from the final reviewed source tree:

```bash
python -m pip install build twine
python -m build --no-isolation
python -m twine check dist/*
```

`dist/` should contain only the wheel and source distribution for the same
version.
