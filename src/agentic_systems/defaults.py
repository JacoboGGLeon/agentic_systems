"""Centralized non-secret defaults for Agentic Systems.

These values are fallbacks for tutorials, local smoke tests and provider
configuration. Environment variables or explicit runtime arguments should be
preferred in production.
"""

DEFAULT_BEDROCK_MODEL_ID = "qwen.qwen3-32b-v1:0"
DEFAULT_OPENAI_MODEL_ID = "gpt-4o-mini"
DEFAULT_VLLM_MODEL_ID = "Qwen/Qwen3-0.6B"
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_VLLM_API_KEY = "EMPTY"

__all__ = [
    "DEFAULT_AWS_REGION",
    "DEFAULT_BEDROCK_MODEL_ID",
    "DEFAULT_OPENAI_MODEL_ID",
    "DEFAULT_VLLM_API_KEY",
    "DEFAULT_VLLM_BASE_URL",
    "DEFAULT_VLLM_MODEL_ID",
]
