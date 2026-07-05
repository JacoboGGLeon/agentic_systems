# Smoke Checklist

Use this checklist before sharing or installing the bundle elsewhere.

## 1. Clean Install

```bash
python -m pip install -U pip
pip install -e .
```

Expected:

```text
install succeeds without requiring AWS, OpenAI, LangGraph or Strands extras
```

## 2. CLI Smoke

```bash
agentic-systems version
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
agentic-systems public-api --all --json
```

Expected:

```text
commands exit with code 0 and print parseable output
```

## 3. Import Smoke

```python
import agentic_systems as toolkit

assert callable(toolkit.tool)
assert callable(toolkit.agent)
assert callable(toolkit.runtime)
assert callable(toolkit.scheduler)
assert callable(toolkit.human_result)
```

## 4. Python-Direct Tool Smoke

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

runtime = toolkit.runtime(provider="python-direct", scheduler=toolkit.scheduler(timeout_s=5))
agent = toolkit.agent(name="calc", tools=[add], runtime=runtime)
result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}}, mode="eval")

assert result.ok
assert result.data["result"] == 5
```

## 5. Tutorial Route Smoke

Confirm these notebooks exist:

```text
tutorials/00_runtime_api.ipynb
tutorials/00_runtime_bedrock_provider_api.ipynb
tutorials/00_runtime_openai_provider_api.ipynb
tutorials/00_runtime_scheduler_api.ipynb
tutorials/01_tool_api.ipynb
tutorials/02_skill_api.ipynb
tutorials/03_agent_api.ipynb
tutorials/04_human_result_api.ipynb
tutorials/05_lineage_memory_api.ipynb
tutorials/06_integrations_strands_api.ipynb
tutorials/07_integrations_openai_runtime_api.ipynb
tutorials/08_system_api.ipynb
tutorials/09_graph_api.ipynb
tutorials/10_environment_eval_api.ipynb
```

## 6. Tests

```bash
python -m pytest -q
python -m compileall -q src tests tutorials
```

Expected:

```text
all tests pass and compileall exits 0
```

## 7. Bundle Hygiene

```text
no wheels
no build directories
no egg-info directories
no __pycache__
no .pytest_cache
no .ipynb_checkpoints
no API keys or credentials
```
