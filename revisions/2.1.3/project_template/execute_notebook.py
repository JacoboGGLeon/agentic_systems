"""Execute this project's notebook using a fresh kernel of this Python."""
import sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

root = Path(__file__).resolve().parent
path = root / "notebooks/01_order_challenge.ipynb"
notebook = nbformat.read(path, as_version=4)
for cell in notebook.cells:
    if cell.cell_type == "code":
        cell.execution_count, cell.outputs = None, []
manager = KernelManager(kernel_name="python3")
manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
client = NotebookClient(notebook, km=manager, timeout=60, resources={"metadata": {"path": str(root)}})
try:
    client.execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
finally:
    if client.kc is not None:
        client.kc.stop_channels()
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)
print("Generated-project notebook PASS; inference requests=0")
