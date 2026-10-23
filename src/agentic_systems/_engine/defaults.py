"""Centralized non-secret defaults for Agentic Systems.

These values are fallbacks for tutorials, local smoke tests and provider
configuration. Environment variables or explicit runtime arguments should be
preferred in production.
"""

DEFAULT_BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"
DEFAULT_OPENAI_MODEL_ID = "gpt-4.1-mini"
DEFAULT_OLLAMA_MODEL_ID = "qwen3:4b-instruct-2507-q4_K_M"
DEFAULT_VLLM_MODEL_ID = "unsloth/Qwen3-4B-Instruct-2507"
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_VLLM_API_KEY = "EMPTY"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_API_KEY = "ollama"

__all__ = [
    "DEFAULT_AWS_REGION",
    "DEFAULT_BEDROCK_MODEL_ID",
    "DEFAULT_OPENAI_MODEL_ID",
    "DEFAULT_VLLM_API_KEY",
    "DEFAULT_OLLAMA_API_KEY",
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_MODEL_ID",
    "DEFAULT_VLLM_BASE_URL",
    "DEFAULT_VLLM_MODEL_ID",
]
