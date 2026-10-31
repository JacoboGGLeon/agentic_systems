"""Exercise the installed CLI, generated project and notebook outside the checkout."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

import agentic_systems as toolkit


def main():
    if "site-packages" not in Path(toolkit.__file__).parts:
        raise ValueError("Install the wheel before validating the scaffolder")
    destination = Path(tempfile.mkdtemp(prefix="agentic-scaffold-dev8-")) / "payment project"
    evidence = Path(os.environ["AGENTIC_VALIDATION_EVIDENCE"]).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONIOENCODING": "utf-8",
           "PYTHONUTF8": "1", "OPENAI_AGENTS_DISABLE_TRACING": "1", "OTEL_SDK_DISABLED": "true"}
    subprocess.run([sys.executable, "-m", "agentic_systems.cli", "new", str(destination)],
                   cwd=destination.parent, env=env, check=True, capture_output=True, text=True, encoding="utf-8")
    env["PYTHONPATH"] = os.pathsep.join((str(destination / "src"), str(Path(toolkit.__file__).parent.parent)))
    rows = []
    commands = ([sys.executable, "app.py"], [sys.executable, "examples/quote.py"],
                [sys.executable, "-m", "pytest", "tests", "-q"])
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=destination, env=env, capture_output=True, text=True, encoding="utf-8", timeout=90)
        (evidence / f"scaffold-{index}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError("Generated project failed; inspect " + str(evidence / f"scaffold-{index}.log"))
    for framework in ("native", "openai-agents", "strands"):
        source = ("import json\nfrom order_fulfillment.offline import enforce_offline\nenforce_offline()\n"
                  "from order_fulfillment.application import demonstrate\nreport=demonstrate(" + repr(framework) + ")\n"
                  "print(json.dumps(report))")
        result = subprocess.run([sys.executable, "-c", source], cwd=destination, env=env, check=True,
                                capture_output=True, text=True, encoding="utf-8", timeout=90)
        report = json.loads(result.stdout)
        rows.append(report)
    notebook = nbformat.read(destination / "notebooks/01_order_challenge.ipynb", 4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(notebook, km=manager, timeout=90, resources={"metadata": {"path": str(destination)}})
    try:
        client.execute(env=env)
    finally:
        if client.kc is not None:
            client.kc.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=False)
    nbformat.write(notebook, evidence / "scaffold-executed.ipynb")
    payload = {"version": toolkit.__version__, "project": str(destination), "frameworks": rows,
               "notebook_passed": True, "generated_tests_passed": True, "inference_requests": 0}
    (evidence / "scaffolder.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": toolkit.__version__, "generated_tests_passed": True, "notebook_passed": True,
                      "frameworks": [row["framework"] for row in rows]}))


if __name__ == "__main__":
    main()
