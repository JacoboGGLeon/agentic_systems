# Agentic Systems Studio

This is the first portable reference product built on Agentic Systems 2.0. It is
both a reusable local component market and a system-of-systems demonstration.

The catalog contains ten systems of different sizes. Every system combines a
deterministic operator on python-runtime with one or more reasoning or review
agents on the selected provider and framework. The same SystemSpec generates:

- executable agents and runtime Skills;
- the Mermaid diagram;
- the Studio UI and CLI inventory;
- the SQLite catalog;
- documentation and tests;
- a self-contained nested bundle.

The included Agentic Systems Creator is the largest reference system. The
scaffolder turns a catalog system into a complete application with source,
tools, runtime and Codex skills, environment and eval entry points, notebook,
tests, Mermaid, manifest, assets and SQLite database.

## Quick start

From the repository root:

    python -m pip install -e .
    python -m pip install -e examples/agentic_systems_studio[ui]
    agentic-studio list
    agentic-studio diagram agentic-systems-creator
    agentic-studio init ./my_app --name my_app
    agentic-studio serve --open-browser

The equivalent notebook launcher is notebooks/02_launch_studio.ipynb. It starts
the same loopback-only server, waits for the Streamlit health endpoint and shows
an HTML button targeting /jupyterlab/default/proxy/8501/. The CLI also prints
that proxy URL for JupyterLab environments.

Live execution is explicit:

    agentic-studio run data-quality --provider ollama-runtime --framework agentic-systems
    agentic-studio compose data-quality decision-intelligence --mode sequential --provider openai-runtime

Provider credentials are read from the environment and are never copied into
SQLite, manifests or bundles.

## Recommended local Ollama model

Use the instruction-tuned Q4 model for agents and tool use:

    ollama pull qwen3:4b-instruct
    OLLAMA_MODEL=qwen3:4b-instruct

The local qwen3:4b alias may resolve to the Q4 thinking variant. That variant
spends a much larger completion budget on internal reasoning and can exhaust the
limit before producing a final answer. Lower-bit Q3 or Q2 builds can be faster
or smaller, but are not the reference default because instruction following and
tool selection are more fragile. See docs/LIVE_VALIDATION.md for measured runs.

## Composition model

A tool is a deterministic operation. A runtime Skill packages tools and
instructions for an Agent. An Agent is one computation unit. A System connects
units through an execution plan. A Studio composition connects complete
CompiledSystem objects and returns one hierarchical RunResult.

This makes the bundle recursive: the top-level Studio bundle contains ten
independently reusable system bundles, while remaining executable as a single
system-of-systems.
