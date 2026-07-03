from __future__ import annotations


def test_notebook_helpers_are_public_top_level_imports():
    from agentic_systems import (
        configure_notebook_environment,
        eval_report_output,
        maybe_show_trace,
        run_result_output,
        show_json,
    )

    assert callable(configure_notebook_environment)
    assert callable(show_json)
    assert callable(run_result_output)
    assert callable(eval_report_output)
    assert callable(maybe_show_trace)
