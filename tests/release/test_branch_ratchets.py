from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _config(name: str) -> ConfigParser:
    parser = ConfigParser()
    assert parser.read(ROOT / name, encoding="utf-8")
    return parser


def test_branch_ratchets_are_separate_blocking_and_never_placeholders():
    expected = {
        ".coveragerc-core-branches": ("agentic_systems", 98.1),
        ".coveragerc-providers-branches": ("agentic_systems.providers", 97.7),
        ".coveragerc-frameworks-branches": ("agentic_systems.integrations", 98.8),
    }
    for name, (source, threshold) in expected.items():
        parser = _config(name)
        sources = {
            value
            for value in parser.get("run", "source").splitlines()
            if value
        }
        assert parser.getboolean("run", "branch") is True
        assert sources == {source}
        assert parser.getfloat("report", "fail_under") == threshold
        assert threshold > 0
