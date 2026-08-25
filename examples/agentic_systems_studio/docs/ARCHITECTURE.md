# Conversational Studio architecture

Studio intentionally exposes one Agentic System through two entry points.

```text
.env
  -> ConversationConfig
  -> deterministic context Agent (python-runtime)
  -> reasoning Agent (selected provider + selected framework)
  -> normalized RunResult
        |- notebook
        `- Streamlit chat
```

The application does not branch on provider or framework. Agentic Systems owns
runtime resolution and adapter selection. The deterministic boundary bounds chat
history and offers arithmetic evidence; the reasoning boundary owns language.
Changing provider/framework means editing `.env` and restarting the application.

No credential, model cache, conversation database or live evidence is embedded in
the Studio bundle. ADA/JupyterLab access uses a loopback Streamlit process plus the
platform proxy path.
