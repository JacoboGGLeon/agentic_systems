"""Agentic Systems Studio: executable catalog, composition and scaffolding."""

from .catalog import SYSTEM_BY_ID, SYSTEM_SPECS, StageSpec, SystemSpec, get_system_spec
from .scaffolder import ScaffoldReport, scaffold_application
from .server import (
    StudioServer,
    serve_studio,
    start_studio_server,
    studio_button_html,
    studio_proxy_url,
)
from .store import StudioStore
from .systems import (
    StudioComposition,
    StudioConfig,
    StudioSystem,
    build_all,
    build_system,
    compose_systems,
)

__all__ = [
    "SYSTEM_BY_ID",
    "SYSTEM_SPECS",
    "ScaffoldReport",
    "StageSpec",
    "StudioComposition",
    "StudioConfig",
    "StudioStore",
    "StudioSystem",
    "SystemSpec",
    "build_all",
    "build_system",
    "compose_systems",
    "get_system_spec",
    "scaffold_application",
    "serve_studio",
    "start_studio_server",
    "studio_button_html",
    "studio_proxy_url",
    "StudioServer",
]
