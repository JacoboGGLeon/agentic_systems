from __future__ import annotations

import agentic_systems as lab


def test_tool_expectation_any_of_allowed() -> None:
    result = lab.validate_tool_expectation(
        ["nl2sql"],
        {"any_of": ["free_sql", "nl2sql"], "allowed": ["free_sql", "nl2sql"]},
    )
    assert result["ok"]
    assert result["rule"] == "any_of"


def test_tool_expectation_all_of_detects_missing() -> None:
    result = lab.validate_tool_expectation(
        ["free_sql"],
        {"all_of": ["free_sql", "nl2sql"], "allowed": ["free_sql", "nl2sql"]},
    )
    assert not result["ok"]
    assert result["missing"] == ["nl2sql"]


def test_tool_expectation_exactly_detects_extra() -> None:
    result = lab.validate_tool_expectation(["free_sql", "nl2sql"], {"exactly": ["free_sql"]})
    assert not result["ok"]
    assert result["extra"] == ["nl2sql"]


def test_expect_namespace_builds_tool_expectations() -> None:
    assert lab.expect.exactly("free_sql") == {"exactly": ["free_sql"]}
    assert lab.expect.any_of("free_sql", "nl2sql") == {"any_of": ["free_sql", "nl2sql"], "allowed": ["free_sql", "nl2sql"]}
    assert lab.expect.all_of("free_sql", "nl2sql") == {"all_of": ["free_sql", "nl2sql"], "allowed": ["free_sql", "nl2sql"]}
    assert lab.validate_tool_expectation(["nl2sql"], lab.expect.any_of("free_sql", "nl2sql"))["ok"] is True
