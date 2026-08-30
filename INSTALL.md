# Install

The Python distribution is named `agentic-systems`. Version 2.1.0 is currently
published as a certified wheel and source archive in the GitHub release; PyPI
still serves the earlier 2.0.0 line. The commands below therefore use the
downloaded 2.1 wheel so the installed code matches this documentation.

## Core Package

```bash
python -m pip install -U pip
python -m pip install ./agentic_systems-2.1.0-py3-none-any.whl
```

The core install includes the public API, CLI, deterministic Python runtime,
tools, skills, agents, systems, graphs, environments, evals, contracts, lineage
memory and human-readable results. It does not import or install optional
provider/framework SDKs.

## Optional Extras

Install only the boundaries you use:

```bash
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[openai]"
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[openai-agents]"
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[bedrock]"
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[langgraph]"
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[strands]"
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[vllm-client]"
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[vllm-server]"  # GPU/Linux host only
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[dev]"
```

| Extra | Purpose |
|---|---|
| `openai` | OpenAI plus OpenAI-compatible client routes, including Ollama and remote vLLM. |
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
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[openai]"
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_MODEL="your-model"
export VLLM_API_KEY="EMPTY"
```

Ollama uses that same lightweight client dependency, but retains its own
Provider identity and environment contract:

```bash
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[openai]"
export OLLAMA_BASE_URL="http://127.0.0.1:11434/v1"
export OLLAMA_MODEL="qwen3:4b-instruct-2507-q4_K_M"
export RUN_OLLAMA_LIVE=1
```

The model name is illustrative. It must already exist in the configured Ollama
server; Agentic Systems does not install Ollama, pull a model or start its
process.

## Stable Version

Install the exact downloaded artifact when reproducibility matters:

```bash
python -m pip install ./agentic_systems-2.1.0-py3-none-any.whl
```

Verify its SHA256 against `SHA256SUMS-2.1.0.txt` from the same GitHub release
before installing it in a controlled environment.

## From GitHub

Use this only when you intentionally want the current `main` branch rather than
the certified 2.1.0 release artifact:

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
