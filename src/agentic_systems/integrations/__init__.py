"""Integration namespace for external orchestration/framework adapters.

Integrations are optional and sit outside the active fundamentals +
accountability path. Importing this namespace does not require LangGraph to be
installed.
"""

from __future__ import annotations

from .boundary import (
    FRAMEWORK_BOUNDARY_SCHEMA_VERSION,
    GRAPH_BOUNDARY_SCHEMA_VERSION,
    PRESERVED_RUN_RESULT_FIELDS,
    FrameworkProfile,
    FrameworkProjectionReport,
    GraphBoundary,
    describe_graph_boundary,
    evaluate_framework_projection,
    framework_profile,
    framework_profiles,
)

__all__ = [
    "langgraph",
    "FRAMEWORK_BOUNDARY_SCHEMA_VERSION",
    "GRAPH_BOUNDARY_SCHEMA_VERSION",
    "PRESERVED_RUN_RESULT_FIELDS",
    "FrameworkProfile",
    "FrameworkProjectionReport",
    "GraphBoundary",
    "framework_profile",
    "framework_profiles",
    "describe_graph_boundary",
    "evaluate_framework_projection",
]
