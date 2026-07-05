# Install

Agentic Systems is published on PyPI as `agentic-systems`.

## PyPI

Install the core library:

```bash
python -m pip install -U pip
python -m pip install agentic-systems
```

Core install includes the public API, CLI, `python-direct`, tools, skills, agents, systems, graphs, environments, evals, contracts, lineage memory and human-readable results.

It does not install optional backend SDKs such as OpenAI, boto3, LangGraph, JupyterLab or vLLM.

## Optional Extras

Install only what you need:

```bash
python -m pip install "agentic-systems[openai]"
python -m pip install "agentic-systems[bedrock]"
python -m pip install "agentic-systems[langgraph]"
python -m pip install "agentic-systems[tutorials]"
python -m pip install "agentic-systems[dev]"
python -m pip install "agentic-systems[all]"
```

`vllm-runtime` uses an OpenAI-compatible vLLM server. The Agentic Systems package does not start or install the vLLM server for you. In a GPU environment, install and run vLLM separately:

```bash
python -m pip install vllm
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen3-0.6B --host 0.0.0.0 --port 8000
```

Then point Agentic Systems to the server:

```bash
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_API_KEY="EMPTY"
```

## From GitHub

Use this when you want the latest `main` branch instead of the PyPI release:

```bash
python -m pip install git+https://github.com/JacoboGGLeon/agentic_systems.git
```

## Local Development

From a cloned repo:

```bash
python -m pip install -U pip
python -m pip install -e ".[dev,tutorials,all]"
```

## Smoke Test

```bash
python - <<'PY'
import agentic_systems as toolkit
print("agentic_systems", toolkit.__version__)
print(callable(toolkit.tool), callable(toolkit.agent), callable(toolkit.runtime))
PY
```

CLI smoke:

```bash
agentic-systems doctor
```

## Python-Direct Runtime

```bash
python - <<'PY'
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

runtime = toolkit.runtime(provider="python-direct", scheduler=toolkit.scheduler(timeout_s=5, max_retries=0))
agent = toolkit.agent(name="calc", tools=[add], runtime=runtime)
result = agent.run({"tool": "add", "input": {"a": 1, "b": 2}}, mode="eval")
print(result.ok, result.data["result"])
PY
```

## Tutorials

```bash
python -m pip install "agentic-systems[tutorials,openai,langgraph]"
jupyter lab tutorials
```

For local repo notebooks, install the repo in editable mode first:

```bash
python -m pip install -e ".[tutorials,openai,langgraph]"
jupyter lab tutorials
```

## Build From Source

```bash
python -m pip install build twine
python -m build --no-isolation
python -m twine check dist/*
```

`dist/` should contain only the wheel and source distribution for `agentic_systems`.
