"""Public Bedrock runtime facade.

Implementation details live in :mod:`agentic_systems.providers.bedrock`; this
module retains the historical import path and the public ``BedrockRuntime``
class definition.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

import boto3

from ..defaults import DEFAULT_AWS_REGION
from .bedrock.converse import _ConverseMixin
from .bedrock.identity import _IdentityMixin
from .bedrock.langgraph import _LangGraphMixin
from .bedrock.models import (
    BedrockRunResult,
    RuntimeToolCallRecord,
    RuntimeToolSpec,
    ToolEnvelope,
)
from .bedrock.tools import _ToolsMixin



class BedrockRuntime(
    _IdentityMixin,
    _ToolsMixin,
    _ConverseMixin,
    _LangGraphMixin,
):
    """Bedrock-first runtime with a stable public API."""

    def __init__(
        self,
        *,
        model_id: str,
        region_name: Optional[str] = None,
        max_tokens_default: int = 800,
        temperature_default: float = 0.0,
        logger_name: str = "agentic_systems",
    ) -> None:
        self.model_id = model_id
        self.max_tokens_default = max_tokens_default
        self.temperature_default = temperature_default

        self.logger = logging.getLogger(logger_name)
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO, format="%(levelname)s - %(message)s"
            )

        self.session = boto3.Session(region_name=region_name)
        self.region_name = (
            self.session.region_name
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or DEFAULT_AWS_REGION
        )

        self.runtime = boto3.client("bedrock-runtime", region_name=self.region_name)
        self.bedrock = boto3.client("bedrock", region_name=self.region_name)
        self.sts = boto3.client("sts", region_name=self.region_name)

        self._tools: Dict[str, RuntimeToolSpec] = {}


__all__ = [
    "BedrockRuntime",
    "BedrockRunResult",
    "RuntimeToolCallRecord",
    "RuntimeToolSpec",
    "ToolEnvelope",
]
