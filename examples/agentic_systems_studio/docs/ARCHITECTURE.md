# Conversational Studio architecture

Studio exposes one Agentic System through direct execution and capability-aware
presentation adapters.

```text
.env
  → ConversationConfig
  → deterministic context Agent (python-runtime)
  → reasoning Agent (selected provider + selected framework)
  → normalized RunResult
        ├─ direct notebook execution
        ├─ Streamlit chat (local, SageMaker/ADA proxy, Colab proxy)
        └─ Jupyter widget chat (explicit alternative)
```

The application does not branch its agentic logic on provider, framework or UI.
Agentic Systems owns runtime resolution and adapter selection. The deterministic
boundary bounds chat history and offers arithmetic evidence; the reasoning
boundary owns language. Changing provider/framework means selecting another
configured route or editing `.env` when the runtime contract itself changes.

Streamlit and the notebook widget call the same ConversationalStudio.run()
method and render the same normalized RunResult, lineage, processing and usage
projections. The host capability changes only transport: Colab uses its
authenticated kernel-port proxy, ADA/JupyterLab uses its platform proxy path and
local execution uses loopback. Notebook-native presentation is an explicit
alternative, never a provider-specific branch or silent fallback.
No credential, model cache, conversation database or live evidence is embedded
in the Studio bundle.
