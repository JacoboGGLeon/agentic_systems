from __future__ import annotations

import sys
from pathlib import Path

from agentic_systems import configure_notebook_environment


def test_configure_notebook_environment_adds_repo_root_and_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path = [p for p in sys.path if p not in {str(repo_root), str(repo_root / "src")}]

    configured = configure_notebook_environment(repo_root)

    assert configured == repo_root
    assert str(repo_root) in sys.path
    assert str(repo_root / "src") in sys.path
    import agentic_systems as lab

    assert callable(lab.tool)
