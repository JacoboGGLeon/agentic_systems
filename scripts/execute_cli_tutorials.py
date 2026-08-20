"""Execute CLI tutorial notebooks in place and verify preserved Rich output."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = ROOT / "tutorials" / "cli"

def _execute_notebook(client: NotebookClient):
    if sys.platform != "win32":
        return client.execute(cwd=str(ROOT))

    loop = asyncio.SelectorEventLoop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            client.async_execute(cwd=str(ROOT))
        )
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def _selected_notebooks(selected: str | None) -> list[Path]:
    if selected is None:
        return sorted(CLI_ROOT.rglob("*.ipynb"))
    root = CLI_ROOT.resolve()
    candidate = (root / selected).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("--notebook must resolve below tutorials/cli.")
    if candidate.suffix != ".ipynb" or not candidate.is_file():
        raise FileNotFoundError(candidate)
    return [candidate]



def execute(*, timeout: int = 180, notebook: str | None = None) -> int:
    notebooks = _selected_notebooks(notebook)
    if not notebooks:
        raise RuntimeError("No CLI notebooks were generated.")

    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        client = NotebookClient(
            notebook,
            timeout=timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        )
        executed = _execute_notebook(client)
        rich_outputs = [
            output.get("text", "")
            for cell in executed.cells
            if cell.cell_type == "code"
            for output in cell.get("outputs", [])
            if output.get("output_type") == "stream"
        ]
        combined = "\n".join(rich_outputs)
        if "$ " not in combined:
            raise AssertionError(f"{path}: CLI command output was not preserved.")
        if not ("+" in combined and "|" in combined):
            raise AssertionError(f"{path}: Rich border evidence is missing.")
        nbformat.write(executed, path)
        print(path.relative_to(ROOT))

    print(f"executed={len(notebooks)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--notebook",
        help="Path below tutorials/cli, for example providers/04_ollama.ipynb.",
    )
    args = parser.parse_args()
    return execute(timeout=args.timeout, notebook=args.notebook)


if __name__ == "__main__":
    raise SystemExit(main())
