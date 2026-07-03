"""Notebook helper exports must remain stable for tutorials."""


def test_notebook_helpers_export_from_top_level_package():
    from agentic_systems import configure_notebook_environment, show_json

    assert callable(configure_notebook_environment)
    assert callable(show_json)


def test_configure_notebook_environment_adds_requested_root(tmp_path):
    from agentic_systems import configure_notebook_environment

    root = configure_notebook_environment(tmp_path, add_src=False)
    assert root == tmp_path.resolve()
