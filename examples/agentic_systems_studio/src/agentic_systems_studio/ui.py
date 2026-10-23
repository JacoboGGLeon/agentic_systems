"""Streamlit chat UI for the portable Agentic Systems Studio."""

from __future__ import annotations

import streamlit as st

from agentic_systems_studio.conversation import (
    ConversationConfig,
    build_conversational_system,
    configured_provider_names,
)
from agentic_systems_studio.routes import FRAMEWORK_NAMES
from agentic_systems_studio.environment import load_studio_environment
from agentic_systems_studio.presentation import (
    processing_mark,
    public_result_payload,
    usage_mark,
)


def main():
    st.set_page_config(
        page_title="Agentic Systems Studio",
        page_icon="🤖",
        layout="centered",
    )


    def _system(config: ConversationConfig):
        return build_conversational_system(config)


    try:
        environment_path = load_studio_environment()
    except FileNotFoundError:
        environment_path = None
    default_config = ConversationConfig.from_environment()

    with st.sidebar:
        st.header("Model and execution")
        providers = configured_provider_names()
        provider = st.selectbox(
            "Provider",
            providers,
            key="provider",
            index=providers.index(default_config.provider)
            if default_config.provider in providers
            else 0,
            format_func=lambda value: (
                "python-runtime (deterministic Hello World mock)"
                if value == "python-runtime"
                else value
            ),
        )
        frameworks = tuple(FRAMEWORK_NAMES)
        framework = st.selectbox(
            "Framework",
            frameworks,
            key="framework",
            index=frameworks.index(default_config.framework)
            if default_config.framework in frameworks
            else 0,
        )
        config = ConversationConfig.from_environment(
            provider=provider,
            framework=framework,
        )
        with st.expander("Connection details"):
            st.json(
            {
                "source": ".env" if environment_path else "process environment; Python needs no credentials",
                "path": str(environment_path) if environment_path else None,
                "provider": config.provider,
                "framework": config.framework,
                "model": config.reasoning_runtime().model,
                "timeout_s": config.timeout_s,
            },
                expanded=False,
            )
        st.caption(
            "Selections apply to this session only. Credentials and discovered routes "
            "remain owned by `.env` or the managed host environment."
        )
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
            if message.get("processing"):
                st.caption(message["processing"])
            if message.get("usage"):
                st.caption(message["usage"])

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
                    mark = processing_mark(result)
                    usage = usage_mark(result)
                    st.caption(mark)
                    st.caption(usage)
                    messages.append(
                        {
                            "role": "assistant",
                            "content": result.text,
                            "processing": mark,
                            "usage": usage,
                        }
                    )
                    st.session_state["last_result"] = result
                except Exception as exc:
                    st.error("Execution failed without provider fallback.")
                    st.exception(exc)

    result = st.session_state.get("last_result")
    if result is not None:
        with st.expander("Latest normalized RunResult"):
            st.json(public_result_payload(result), expanded=False)

    with st.expander("Compiled system contract"):
        st.json(studio.inspect(), expanded=False)

    st.caption(
        f"provider={config.provider} · framework={config.framework} · "
        f"model={config.model or 'provider default'}"
    )

    with st.expander("Framework capabilities"):
        scenario = st.selectbox("Example", ("LangGraph checkpoint", "OpenAI Agents handoff", "Strands MCP", "Strands A2A", "Four frameworks · Python", "Four frameworks · mixed providers"), key="example")
        st.caption("Real SDK capabilities. MCP/A2A run isolated local services. External models share the authorized campaign budget.")
        if st.button("Run example"):
            st.session_state.pop("lab_report", None)
            try:
                from agentic_systems_studio.lab import probes
                from agentic_systems_studio.budget import ensure_budget
                budget = ensure_budget() if config.provider != "python-runtime" or scenario.endswith("mixed providers") else None
                if scenario == "LangGraph checkpoint":
                    from agentic_systems_studio.lab.checkpoint import run
                    report = run()
                elif scenario == "OpenAI Agents handoff":
                    report = probes.handoffs(config.provider)
                elif scenario.startswith("Strands"):
                    report = probes.protocols(config.provider, "mcp" if scenario.endswith("MCP") else "a2a", budget)
                else:
                    report = probes.interop(scenario.endswith("mixed providers"))
                st.session_state["lab_report"] = report
                st.success("Example completed with recorded evidence")
            except Exception as exc:
                st.error(str(exc))
        if "lab_report" in st.session_state:
            st.json(st.session_state["lab_report"], expanded=False)


if __name__ == "__main__":
    main()
