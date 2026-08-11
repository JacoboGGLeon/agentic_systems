from __future__ import annotations

from pathlib import Path

import agentic_systems as lab



def test_api_reference_documents_complete_public_api() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    api_doc = (repo_root / "docs" / "API.md").read_text(encoding="utf-8")

    missing = [name for name in lab.__all__ if name not in api_doc]

    assert missing == []
