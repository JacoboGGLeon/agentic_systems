# Agentic Systems Studio · 2.1.8

Studio is a separate application. Install the matching SDK wheel, then:

```bash
python -m pip install "./examples/agentic_systems_studio[ui,notebook]"
python -m streamlit run examples/agentic_systems_studio/src/agentic_systems_studio/ui.py
```

[Notebook](notebooks/01_studio.ipynb) · [English reading view](notebooks/01_studio.md).

```python
from agentic_systems_studio import ConversationConfig, build_conversational_system
app = build_conversational_system(ConversationConfig(provider='python-runtime', framework='native'))
result = app.run('Hello')
assert result.ok
print(result.data)
```

The controller uses LangGraph; native, openai-agents and strands implement actors. Each node holds a business payload envelope rather than complete result trees. Public output retains answer, history, validation, events and lineage. Credentials remain outside state.

Separate checks cover controller/conversation, UI, handoffs and MCP/A2A. Local services use fixtures without language-model inference; model-backed actors are validated separately. Configure environment variables and AGENTIC_BUDGET_FILE with an authorized persistent counter for inference. A Python fixture does not certify model conversation quality or every UI control.

[The explicit demonstration](example.py) exposes Graph, Tools, Skills, Agent, System, Context and Memory. The full controller API is an additional application integration rather than a substitute for those declarations; the notebook shows both boundaries.

The Python controller chat uses a deterministic hello_world fixture. It does not interpret language or automatically select the calculator. safe_calculate can be invoked explicitly. Recorded model-backed controller checks cover history and calculator invocation, not every UI control. [Historical validation](../../revisions/2.1.4/contracts-dev5/REPORT.md) retains its original provenance.

## Run from a repository checkout

Follow the [shared execution guide](../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/agentic_systems_studio/example.py
```

This command runs the offline profile only. Its validation scope is separate from live provider campaigns.
