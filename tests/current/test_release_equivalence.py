"""The authorized packaging exception must reject executable changes."""
import hashlib
import importlib.util
from pathlib import Path
import zipfile

import pytest


def load():
    import sys
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("seal_release_214", scripts / "seal_release_214.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("change", ["none", "logic", "extra", "missing", "version"])
def test_payload_equivalence(tmp_path, change):
    module = load()
    init = b'__version__ = "2.1.4"\n'
    logic = b'def work(): return 1\n'
    policy = {"reference_python_sha256": {"agentic_systems/__init__.py": "reference-version-hash",
              "agentic_systems/work.py": hashlib.sha256(logic).hexdigest()},
              "stable_init_sha256": hashlib.sha256(init).hexdigest()}
    wheel = tmp_path / "fixture.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agentic_systems/__init__.py", init if change != "version" else b'__version__="9.0"')
        if change != "missing":
            archive.writestr("agentic_systems/work.py", logic if change != "logic" else b'def work(): return 2\n')
        if change == "extra":
            archive.writestr("agentic_systems/extra.py", b'pass')
    if change == "none":
        assert module.verify_logic(wheel, policy) == 2
    else:
        with pytest.raises(ValueError):
            module.verify_logic(wheel, policy)
