"""Error types for Agentic Systems 1.0."""

from __future__ import annotations


class AgenticSystemError(Exception):
    """Base class for Agentic Systems errors."""


class ToolContractError(AgenticSystemError):
    """Raised when a tool does not satisfy the public tool contract."""


class AgentContractError(AgenticSystemError):
    """Raised when an agent contract is invalid or violated before execution."""


class RunPolicyError(AgenticSystemError):
    """Raised when a run policy is invalid."""


class EngineError(AgenticSystemError):
    """Raised by execution engines."""


class GraphContractError(AgenticSystemError):
    """Raised when LangGraph node mapping is invalid."""


class SkillLoadError(AgenticSystemError):
    """Raised when a Skill asset loader package cannot be loaded."""


class EvaluationError(AgenticSystemError):
    """Raised by eval helpers."""
