"""Execute the saved notebook cells offline in one Python process."""
from pathlib import Path
import json

root = Path(__file__).resolve().parent
namespace = {"__name__": "__main__"}
notebook = json.loads((root / "notebooks/01_order_challenge.ipynb").read_text(encoding="utf-8"))
for cell in notebook["cells"]:
    if cell["cell_type"] == "code":
        exec(compile("".join(cell["source"]), "01_order_challenge.ipynb", "exec"), namespace)
