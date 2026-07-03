from __future__ import annotations

from pathlib import Path

import agentic_systems as lab

from ._load_legacy import export_legacy_tests

export_legacy_tests(
    globals(),
    'core_phase2_coverage',
    'multi_agent_state_contract',
    'checkpoint_04k_user_first_tutorials',
    'checkpoint_12b_fundamentals_comparison',
)


def test_api_reference_documents_complete_public_api() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    api_doc = (repo_root / "docs" / "API.md").read_text(encoding="utf-8")

    missing = [name for name in lab.PUBLIC_API if name not in api_doc]

    assert missing == []
