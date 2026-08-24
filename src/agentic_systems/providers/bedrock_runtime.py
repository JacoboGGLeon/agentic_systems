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
from botocore.config import Config

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


def _bedrock_streaming_from_environment() -> bool:
    """Parse the canonical Bedrock streaming selector from ``.env``/environment."""

    raw = (os.getenv("BEDROCK_STREAMING") or "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(
        "BEDROCK_STREAMING must be one of 1/0, true/false, yes/no, or on/off."
    )


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
        bedrock_api_key = (os.getenv("AWS_BEARER_TOKEN_BEDROCK") or "").strip()
        self.auth_mode = (
            "bedrock-api-key" if bedrock_api_key else "aws-credential-chain"
        )
        self.streaming = _bedrock_streaming_from_environment()
        self.region_name = (
            self.session.region_name
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or DEFAULT_AWS_REGION
        )

        client_kwargs: dict[str, object] = {"region_name": self.region_name}
        if self.auth_mode == "aws-credential-chain":
            # Botocore treats an existing but empty AWS_BEARER_TOKEN_BEDROCK as
            # a bearer-token signal. Agentic Systems defines an empty .env value
            # as IAM mode, so force SigV4 without mutating canonical config.
            client_kwargs["config"] = Config(signature_version="v4")

        self.runtime = self.session.client("bedrock-runtime", **client_kwargs)
        self.bedrock = self.session.client("bedrock", **client_kwargs)
        self.sts = (
            None
            if self.auth_mode == "bedrock-api-key"
            else self.session.client("sts", **client_kwargs)
        )
        self._tools: Dict[str, RuntimeToolSpec] = {}


__all__ = [
    "BedrockRuntime",
    "BedrockRunResult",
    "RuntimeToolCallRecord",
    "RuntimeToolSpec",
    "ToolEnvelope",
]
