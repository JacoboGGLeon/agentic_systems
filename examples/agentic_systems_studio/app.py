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
from agentic_systems_studio.creator import create_application
from agentic_systems_studio.scaffolder import ScaffoldReport, scaffold_application
from agentic_systems_studio.store import StudioStore
from agentic_systems_studio.systems import StudioConfig, build_system, compose_systems


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "studio.db"

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


def render_creator_result(result) -> None:
    artifact = result.data.get("artifact") if isinstance(result.data, dict) else None
    if not artifact:
        st.error(result.text or "The Creator did not produce an artifact.")
        st.json(result_payload(result), expanded=False)
        return

    if result.ok:
        st.success(result.text)
    else:
        st.error(result.text)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Generated files", artifact["file_count"])
    metric_columns[1].metric(
        "Contract checks",
        sum(bool(value) for value in artifact["validation"]["checks"].values()),
    )
    metric_columns[2].metric(
        "Validation",
        "PASSED" if artifact["validation"]["ok"] else "FAILED",
    )
    st.caption("Generated project")
    st.code(artifact["root"])

    output_tabs = st.tabs(
        ["Files", "Validation", "Manifest", "Mermaid", "Run", "Normalized result"]
    )
    with output_tabs[0]:
        st.code("\n".join(artifact["files"]), language="text")
        root = Path(artifact["root"])
        report = ScaffoldReport(
            root=root,
            package_name=artifact["package_name"],
            system_id=artifact["system_id"],
            files=tuple(root / relative for relative in artifact["files"]),
        )
        st.download_button(
            "Download generated Agentic System (.zip)",
            data=report.archive_bytes(),
            file_name=artifact["archive_name"],
            mime="application/zip",
            key="download-created-agentic-system",
        )
    with output_tabs[1]:
        st.dataframe(
            [
                {"check": name, "passed": passed}
                for name, passed in artifact["validation"]["checks"].items()
            ],
            use_container_width=True,
            hide_index=True,
        )
        if artifact["validation"]["issues"]:
            st.json(artifact["validation"]["issues"], expanded=True)
    with output_tabs[2]:
        st.json(artifact["manifest"], expanded=True)
    with output_tabs[3]:
        render_mermaid(artifact["mermaid"], height=340)
    with output_tabs[4]:
        st.code(
            f"cd {artifact['root']}\n"
            "python -m pip install -e .\n"
            f"{artifact['run_command']}",
            language="bash",
        )
    with output_tabs[5]:
        st.json(result_payload(result), expanded=False)


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
    max_tokens = st.number_input(
        "Maximum output tokens per reasoning turn", min_value=64, value=1024
    )
    db_path = Path(
        st.text_input(
            "SQLite evidence path",
            value=str(DEFAULT_DB_PATH),
        )
    )
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
        format_func=lambda value: next(
            spec.name for spec in SYSTEM_SPECS if spec.id == value
        ),
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
    is_creator = system_id == "agentic-systems-creator"
    if is_creator:
        st.subheader("Generation contract")
        creator_left, creator_right = st.columns(2)
        with creator_left:
            creator_name = st.text_input(
                "Generated application name",
                value="incident_response_application",
            )
            creator_template = st.selectbox(
                "Executable topology template",
                [
                    item.id
                    for item in SYSTEM_SPECS
                    if item.id != "agentic-systems-creator"
                ],
                index=2,
            )
        with creator_right:
            creator_target = st.text_input(
                "Generated project directory",
                value="dist/incident_response_application",
            )
            creator_overwrite = st.checkbox(
                "Overwrite only files at the exact generated target",
                key="creator-overwrite",
            )
        st.caption(
            "Success requires blueprint reasoning, physical project generation and "
            "artifact validation. A plan without files is a failed Creator run."
        )

    action_label = (
        "Generate and validate Agentic System" if is_creator else "Run selected system"
    )
    if st.button(action_label, type="primary"):
        with st.spinner(
            "Designing, generating and validating application..."
            if is_creator
            else "Executing system..."
        ):
            try:
                if is_creator:
                    result = create_application(
                        run_input,
                        creator_target,
                        name=creator_name,
                        template_system_id=creator_template,
                        config=config,
                        overwrite=creator_overwrite,
                    )
                else:
                    system = build_system(system_id, config)
                    result = system.run(run_input)
                run_id = StudioStore(db_path).record_run(
                    system_id=system_id,
                    provider=provider,
                    framework=framework,
                    input=run_input,
                    result=result,
                )
                st.session_state["latest_system_id"] = system_id
                st.session_state["latest_system_result"] = result
                st.session_state["latest_run_id"] = run_id
            except Exception as exc:
                st.exception(exc)

    if (
        st.session_state.get("latest_system_id") == system_id
        and "latest_system_result" in st.session_state
    ):
        latest_result = st.session_state["latest_system_result"]
        st.caption(f"Recorded run: {st.session_state['latest_run_id']}")
        if is_creator:
            render_creator_result(latest_result)
        else:
            st.success(f"ok={latest_result.ok}")
            st.write(latest_result.text or latest_result.data)
            st.json(result_payload(latest_result), expanded=False)

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
    scaffold_target = st.text_input(
        "Target directory", value="dist/my_agentic_application"
    )
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
