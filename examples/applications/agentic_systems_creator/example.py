"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
from agentic_systems.cli import main


def run():
    destination = Path(tempfile.mkdtemp(prefix="agentic-example-")) / "application"
    with redirect_stdout(StringIO()):
        main(["new", str(destination)])
    assert (destination / "app.py").is_file() and (destination / "tests/test_contract.py").is_file()
    return {"project": str(destination), "version": toolkit.__version__, "status": "generated; project execution validated separately"}
