"""Generate the two canonical Studio notebooks from reviewed source."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def _markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def _code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


def _notebook(cells: list[dict], *, entrypoint: str) -> dict:
    for index, cell in enumerate(cells):
        cell["id"] = f"studio-{entrypoint}-{index:02d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
            "agentic_systems": {
                "version": "2.1.2",
                "application": "conversational-studio",
                "entrypoint": entrypoint,
                "configuration": ".env",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


DIRECT = _notebook(
    [
        _markdown(
            "# Conversational Agentic System\n\n"
            "This is the complete Studio system without a UI. A deterministic Python "
            "Agent bounds conversation context; a reasoning Agent uses the provider and "
            "framework selected by `.env`. The same builder powers the Streamlit app.\n"
        ),
        _markdown(
            "## 1. Configuration contract\n\n"
            "In ADA, copy the bundle-root `.env.example` to the bundle-root `.env`; "
            "that is the only runtime configuration file. No credential is entered in "
            "the notebook and no provider fallback is enabled. Set `RUN_STUDIO_LIVE=1` "
            "when the selected provider is ready.\\n"
        ),
        _code(
            "import os\n\n"
            "import agentic_systems as toolkit\n"
            "from agentic_systems_studio import (\n"
            "    ConversationConfig,\n"
            "    build_conversational_system,\n"
            "    load_studio_environment,\n"
            "    safe_calculate,\n"
            ")\n\n"
            "environment_path = load_studio_environment()\n"
            "config = ConversationConfig.from_environment()\n"
            "RUN_STUDIO_LIVE = (\n"
            "    os.getenv('RUN_STUDIO_LIVE', '0').lower() in {'1', 'true', 'yes'}\n"
            "    and os.getenv('AGENTIC_SYSTEMS_NOTEBOOK_TEST') != '1'\n"
            ")\n"
            "toolkit.show_json({\n"
            "    'environment_path': str(environment_path),\n"
            "    'provider': config.provider,\n"
            "    'framework': config.framework,\n"
            "    'model': config.model,\n"
            "    'run_live': RUN_STUDIO_LIVE,\n"
            "}, title='Studio runtime contract')\n"
        ),
        _markdown(
            "## 2. Deterministic evidence\n\n"
            "The Tool runs without an LM. This verifies the deterministic boundary before "
            "we compile the reasoning runtime.\n"
        ),
        _code(
            "calculation = safe_calculate.run({'expression': '17 * 19'})\n"
            "assert calculation.ok and calculation.data['result'] == 323\n"
            "toolkit.show_json(calculation.data, title='Deterministic Tool evidence')\n"
        ),
        _markdown(
            "## 3. Build and converse\n\n"
            "`build_conversational_system` is provider/framework-agnostic. The result must "
            "retain the selected runtime identity and pass common invariants.\n"
        ),
        _code(
            "if RUN_STUDIO_LIVE:\n"
            "    studio = build_conversational_system(config)\n"
            "    result = studio.run('Explain why 17 * 19 is 323 and use the calculator.')\n"
            "    assert result.ok, result.errors\n"
            "    result.check_invariants()\n"
            "    toolkit.human_result(result, title='Conversational Studio RunResult')\n"
            "else:\n"
            "    studio = None\n"
            "    result = None\n"
            "    toolkit.show_json({'status': 'not-run', 'reason': 'RUN_STUDIO_LIVE=0'})\n"
        ),
        _markdown(
            "## Acceptance\n\n"
            "The run is accepted when the declared provider/framework executes without "
            "fallback, deterministic tool evidence is observable and the final `RunResult` "
            "passes invariants.\n"
        ),
    ],
    entrypoint="notebook",
)


LAUNCH = _notebook(
    [
        _markdown(
            "# Launch the conversational Studio\n\n"
            "This notebook starts the Streamlit wrapper for the same system used in "
            "`00_conversational_system.ipynb`. It binds only to loopback, waits for health "
            "and exposes local and ADA/JupyterLab proxy URLs.\n"
        ),
        _code(
            "import os\n\n"
            "from IPython.display import HTML, display\n"
            "from agentic_systems_studio import (\n"
            "    load_studio_environment,\n"
            "    start_studio_server,\n"
            "    studio_button_html,\n"
            "    studio_proxy_url,\n"
            ")\n\n"
            "environment_path = load_studio_environment()\n"
            "PORT = int(os.getenv('AGENTIC_SYSTEMS_STUDIO_PORT', '8501'))\n"
            "PROXY_PREFIX = os.getenv(\n"
            "    'AGENTIC_SYSTEMS_STUDIO_PROXY_PREFIX',\n"
            "    '/jupyterlab/default/proxy',\n"
            ")\n"
        ),
        _code(
            "studio_server = start_studio_server(port=PORT)\n"
            "direct_url = studio_server.local_url\n"
            "proxy_url = studio_proxy_url(PORT, prefix=PROXY_PREFIX)\n\n"
            "print('Health check: ok')\n"
            "print('Local URL:', direct_url)\n"
            "print('ADA/JupyterLab proxy:', proxy_url)\n"
            "print('Log:', studio_server.log_path)\n"
            "display(HTML(studio_button_html(\n"
            "    direct_url,\n"
            "    label='Open Agentic Systems Studio',\n"
            "    alternate_url=proxy_url,\n"
            "    alternate_label='Open through ADA/JupyterLab proxy',\n"
            ")))\n\n"
            "if os.getenv('AGENTIC_SYSTEMS_NOTEBOOK_TEST') == '1':\n"
            "    studio_server.stop()\n"
        ),
        _markdown(
            "The server intentionally remains active after the launch cell. Stop only the "
            "owned process with `studio_server.stop()` when the session ends.\n"
        ),
    ],
    entrypoint="streamlit",
)


def main() -> None:
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)
    outputs = {
        "00_conversational_system.ipynb": DIRECT,
        "01_launch_studio.ipynb": LAUNCH,
    }
    for name, notebook in outputs.items():
        (NOTEBOOKS / name).write_text(
            json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
