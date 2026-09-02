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
        ├─ Streamlit chat (local, SageMaker, ADA)
        └─ Jupyter widget chat (Colab)
```

The application does not branch its agentic logic on provider, framework or UI.
Agentic Systems owns runtime resolution and adapter selection. The deterministic
boundary bounds chat history and offers arithmetic evidence; the reasoning
boundary owns language. Changing provider/framework means selecting another
configured route or editing `.env` when the runtime contract itself changes.

Streamlit and the notebook widget call the same `ConversationalStudio.run()`
method and render the same normalized RunResult, lineage, processing and usage
projections. The host capability changes only presentation: Colab's kernel proxy
cannot carry Streamlit's WebSocket, so the vLLM notebook uses Jupyter widgets
without opening a public tunnel. ADA/JupyterLab uses a loopback Streamlit process
plus the platform proxy path.

No credential, model cache, conversation database or live evidence is embedded
in the Studio bundle.
