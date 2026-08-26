"""Streamlit chat UI for the portable Agentic Systems Studio."""

from __future__ import annotations

import streamlit as st

from agentic_systems_studio.conversation import (
    ConversationConfig,
    build_conversational_system,
)
from agentic_systems_studio.environment import load_studio_environment


st.set_page_config(
    page_title="Agentic Systems Studio",
    page_icon="🤖",
    layout="centered",
)


def _result_payload(result):
    return result.model_dump(mode="json") if hasattr(result, "model_dump") else result


@st.cache_resource(show_spinner="Compiling Agentic System...")
def _system(config: ConversationConfig):
    return build_conversational_system(config)


environment_path = load_studio_environment()
config = ConversationConfig.from_environment()

with st.sidebar:
    st.header("Runtime contract")
    st.json(
        {
            "source": ".env",
            "path": str(environment_path),
            "provider": config.provider,
            "framework": config.framework,
            "model": config.model or "provider default",
            "timeout_s": config.timeout_s,
        },
        expanded=True,
    )
    st.caption("Change `.env` and restart Studio to change the runtime contract.")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.pop("messages", None)
        st.session_state.pop("last_result", None)
        st.rerun()

st.title("Agentic Systems Studio")
st.caption(
    "One conversational Agentic System. Deterministic Python establishes context and "
    "tool evidence; the selected provider/framework handles language reasoning."
)

try:
    studio = _system(config)
except Exception as exc:
    st.error("The runtime contract declared by .env could not be compiled.")
    st.exception(exc)
    st.stop()

messages = st.session_state.setdefault(
    "messages",
    [
        {
            "role": "assistant",
            "content": "Ready. Ask a question or request a verified calculation.",
        }
    ],
)

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Message the Agentic System"):
    prior_history = list(messages)
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Running deterministic and reasoning boundaries..."):
            try:
                result = studio.run(prompt, history=prior_history)
                st.markdown(result.text)
                messages.append({"role": "assistant", "content": result.text})
                st.session_state["last_result"] = result
            except Exception as exc:
                st.error("Execution failed without provider fallback.")
                st.exception(exc)

result = st.session_state.get("last_result")
if result is not None:
    with st.expander("Latest normalized RunResult"):
        st.json(_result_payload(result), expanded=False)

with st.expander("Compiled system contract"):
    st.json(studio.inspect(), expanded=False)

st.caption(
    f"provider={config.provider} · framework={config.framework} · "
    f"model={config.model or 'provider default'}"
)
