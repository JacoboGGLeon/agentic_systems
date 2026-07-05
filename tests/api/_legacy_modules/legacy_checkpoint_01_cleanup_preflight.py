from __future__ import annotations

import importlib
from pathlib import Path


def test_checkpoint_01_boundary_docs_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "BOUNDARIES.md").exists()
    assert (root / "docs" / "ROADMAP_CHECKPOINTS.md").exists()
    assert (root / "AGENTIC_SYSTEMS_PROGRESS.md").exists()


def test_runtime_scheduler_contracts_are_reserved_without_public_factory() -> None:
    core_runtime = importlib.import_module("agentic_systems.core.runtime")
    core_scheduler = importlib.import_module("agentic_systems.core.scheduler")

    scheduler = core_scheduler.SchedulerConfig(timeout_s=10, max_retries=1)
    runtime = core_runtime.RuntimeConfig(provider="python-runtime", scheduler=scheduler)

    assert scheduler.to_dict()["timeout_s"] == 10
    assert runtime.to_dict()["provider"] == "python-runtime"
    assert runtime.to_dict()["scheduler"]["max_retries"] == 1


def test_canonical_namespaces_remain_importable() -> None:
    import agentic_systems.engines as engines
    import agentic_systems.integrations as integrations

    assert hasattr(engines, "PythonDirectEngine")
    assert hasattr(engines, "BEDROCK_RUNTIME_ENGINE")
    assert hasattr(integrations, "__all__")
    langgraph = importlib.import_module("agentic_systems.integrations.langgraph")
    assert hasattr(langgraph, "graph")
