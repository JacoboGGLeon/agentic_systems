"""Conversational Studio plus compatibility utilities for advanced workflows."""

from .catalog import SYSTEM_BY_ID, SYSTEM_SPECS, StageSpec, SystemSpec, get_system_spec
from .conversation import (
    ConversationConfig,
    ConversationalStudio,
    build_conversational_system,
    prepare_conversation_context,
    safe_calculate,
)
from .environment import (
    find_studio_environment,
    load_studio_environment,
)
from .creator import create_application
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
from .validation import validate_catalog, write_validation_report

__all__ = [
    "SYSTEM_BY_ID",
    "SYSTEM_SPECS",
    "ConversationConfig",
    "ConversationalStudio",
    "ScaffoldReport",
    "StageSpec",
    "StudioComposition",
    "StudioConfig",
    "StudioStore",
    "StudioSystem",
    "SystemSpec",
    "build_all",
    "build_conversational_system",
    "build_system",
    "compose_systems",
    "create_application",
    "find_studio_environment",
    "get_system_spec",
    "load_studio_environment",
    "prepare_conversation_context",
    "safe_calculate",
    "scaffold_application",
    "serve_studio",
    "start_studio_server",
    "studio_button_html",
    "studio_proxy_url",
    "validate_catalog",
    "write_validation_report",
    "StudioServer",
]
