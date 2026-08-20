"""Streamlit UI for the portable Agentic Systems Studio."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from agentic_systems_studio.catalog import SYSTEM_SPECS
from agentic_systems_studio.components import (
    AGENT_ASSETS,
    ENVIRONMENT_ASSETS,
    EVAL_ASSETS,
    SKILL_ASSETS,
    TOOL_ASSETS,
)
from agentic_systems_studio.scaffolder import scaffold_application
from agentic_systems_studio.store import StudioStore
from agentic_systems_studio.systems import StudioConfig, build_system, compose_systems


st.set_page_config(page_title="Agentic Systems Studio", page_icon="??", layout="wide")


def render_mermaid(source: str, *, height: int = 420) -> None:
    escaped = html.escape(source)
    components.html(
        f"""
        <div class="mermaid">{escaped}</div>
        <script type="module">
          import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
          mermaid.initialize({{startOnLoad: true, theme: "dark"}});
        </script>
        """,
        height=height,
        scrolling=True,
    )
    with st.expander("Mermaid source"):
        st.code(source, language="mermaid")


def card(asset) -> None:
    with st.container(border=True):
        st.subheader(asset.name)
        st.caption(asset.id)
        st.write(asset.description)
        st.code(asset.capability)
        st.json(asset.metadata, expanded=False)


def result_payload(result):
    return result.model_dump(mode="json") if hasattr(result, "model_dump") else result


st.title("Agentic Systems Studio")
st.write(
    "A portable market of computation units and complete systems. "
    "The catalog declaration drives execution, Mermaid, SQLite, notebooks, tests and bundles."
)

with st.sidebar:
    st.header("Execution")
    provider = st.selectbox(
        "Reasoning provider",
        ("openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime", "auto"),
    )
    framework = st.selectbox(
        "Agent framework",
        ("agentic-systems", "langgraph", "openai-agents", "strands"),
    )
    model = st.text_input("Model override", value="")
    timeout = st.number_input("Timeout seconds", min_value=5, value=120)
    max_tokens = st.number_input("Maximum output tokens per reasoning turn", min_value=64, value=1024)
    db_path = Path(st.text_input("SQLite evidence path", value="examples/agentic_systems_studio/data/studio.db"))
    config = StudioConfig(
        provider=provider,
        framework=framework,
        model=model or None,
        timeout_s=float(timeout),
        max_tokens=int(max_tokens),
    )
    st.caption("Credentials remain in environment variables and are never persisted.")

tabs = st.tabs(
    [
        "Systems",
        "Composition",
        "Tools",
        "Skills",
        "Agents",
        "Environments",
        "Evals",
        "Scaffolder",
        "Evidence",
    ]
)

with tabs[0]:
    system_id = st.selectbox(
        "Reusable system",
        [spec.id for spec in SYSTEM_SPECS],
        format_func=lambda value: next(spec.name for spec in SYSTEM_SPECS if spec.id == value),
    )
    spec = next(item for item in SYSTEM_SPECS if item.id == system_id)
    left, right = st.columns((2, 1))
    with left:
        render_mermaid(spec.mermaid(provider=provider, framework=framework))
    with right:
        st.metric("Size", spec.size)
        st.metric("Agents", len(spec.stages))
        st.write(spec.summary)
        st.write("Capabilities:", ", ".join(spec.capabilities))
        st.write("Runtime skill:", spec.runtime_skill)
        st.write("Assets:", len(spec.assets))
    run_input = st.text_area("Input", value=spec.sample_input, height=150)
    if st.button("Run selected system", type="primary"):
        with st.spinner("Executing system..."):
            try:
                system = build_system(system_id, config)
                result = system.run(run_input)
                run_id = StudioStore(db_path).record_run(
                    system_id=system_id,
                    provider=provider,
                    framework=framework,
                    input=run_input,
                    result=result,
                )
                st.success(f"Run {run_id} recorded. ok={result.ok}")
                st.write(result.text or result.data)
                st.json(result_payload(result), expanded=False)
            except Exception as exc:
                st.exception(exc)

with tabs[1]:
    selected_ids = st.multiselect(
        "Ordered systems",
        [spec.id for spec in SYSTEM_SPECS],
        default=["data-quality", "decision-intelligence"],
    )
    mode = st.radio("Composition plan", ("sequential", "parallel"), horizontal=True)
    if selected_ids:
        preview = compose_systems(selected_ids, config, mode=mode, validate=False)
        render_mermaid(preview.mermaid(), height=300)
        st.caption(
            "Each node is itself a CompiledSystem. Sequential mode passes one normalized "
            "RunResult payload to the next; parallel mode broadcasts the same input."
        )
        composition_input = st.text_area(
            "Composition input",
            value=preview.systems[0].spec.sample_input,
            key="composition_input",
        )
        if st.button("Run system-of-systems"):
            with st.spinner("Executing composition..."):
                try:
                    composition = compose_systems(selected_ids, config, mode=mode)
                    result = composition.run(composition_input)
                    record_id = StudioStore(db_path).record_composition(
                        mode=mode,
                        system_ids=composition.ids,
                        result=result,
                    )
                    st.success(f"Composition {record_id} recorded. ok={result.ok}")
                    st.json(result_payload(result), expanded=False)
                except Exception as exc:
                    st.exception(exc)
    else:
        st.info("Select at least one system.")

for tab, title, assets in (
    (tabs[2], "Deterministic tools", TOOL_ASSETS),
    (tabs[3], "Runtime skills", SKILL_ASSETS),
    (tabs[4], "Computation agents", AGENT_ASSETS),
    (tabs[5], "Episodic environments", ENVIRONMENT_ASSETS),
    (tabs[6], "Agent and system evals", EVAL_ASSETS),
):
    with tab:
        st.header(title)
        st.caption(f"{len(assets)} reusable assets")
        query = st.text_input("Filter", key=f"filter-{title}")
        visible = [
            asset
            for asset in assets
            if not query or query.lower() in str(asset.to_dict()).lower()
        ]
        columns = st.columns(2)
        for index, asset in enumerate(visible):
            with columns[index % 2]:
                card(asset)

with tabs[7]:
    st.header("Reference application scaffolder")
    st.write(
        "Generates source, tools, runtime and Codex skills, system assembly, "
        "environment/eval entry points, notebook, tests, Mermaid, manifest, assets and SQLite."
    )
    scaffold_name = st.text_input("Application name", value="my_agentic_application")
    scaffold_system = st.selectbox(
        "Topology template",
        [spec.id for spec in SYSTEM_SPECS],
        key="scaffold-system",
    )
    scaffold_target = st.text_input("Target directory", value="dist/my_agentic_application")
    overwrite = st.checkbox("Overwrite files generated at the exact target paths")
    if st.button("Generate application"):
        try:
            report = scaffold_application(
                scaffold_target,
                name=scaffold_name,
                system_id=scaffold_system,
                overwrite=overwrite,
            )
            st.success(f"Generated {len(report.files)} assets in {report.root}")
            st.json(report.to_dict())
        except Exception as exc:
            st.exception(exc)

with tabs[8]:
    store = StudioStore(db_path)
    if st.button("Initialize / refresh catalog database"):
        store.initialize()
    st.json({"path": str(store.path.resolve()), "inventory": store.inventory()})
    st.dataframe(store.recent_runs(), use_container_width=True)
    st.info(
        "The SQLite database stores component manifests and normalized RunResult evidence. "
        "It never stores API keys, bearer tokens or AWS credentials."
    )
