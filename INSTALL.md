# Install

## Core

```bash
python -m pip install -U pip
pip install -e .
```

Core install keeps optional backends out of the default path.

## Extras

```bash
pip install -e '.[bedrock]'
pip install -e '.[langgraph]'
pip install -e '.[tutorials]'
pip install -e '.[dev]'
pip install -e '.[all]'
```

## Smoke

```bash
python - <<'PY'
import agentic_systems as toolkit
print("agentic_systems", toolkit.__version__)
print(callable(toolkit.tool), callable(toolkit.agent), callable(toolkit.runtime))
PY
```

## Python-Direct

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
pip install -e '.[tutorials]'
jupyter lab tutorials
```

## Build

```bash
python -m build --no-isolation
```

`dist/` should contain only the wheel and source distribution for `agentic_systems`.
