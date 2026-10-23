"""Application choices and explicit environment configuration, without SDK internals."""
import os
import agentic_systems as toolkit

PROVIDER_NAMES = ("python-runtime", "openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime")
FRAMEWORK_NAMES = ("native", "langgraph", "openai-agents", "strands")


def values(provider):
    if provider not in PROVIDER_NAMES:
        raise ValueError("Choose an explicit provider; Studio has no auto or fallback")
    if provider == "python-runtime":
        return {"model": "python-runtime", "endpoint": None, "api_key": None, "region": None}
    prefix = {"openai-runtime": "OPENAI", "ollama-runtime": "OLLAMA", "bedrock-runtime": "BEDROCK", "vllm-runtime": "VLLM"}[provider]
    return {"model": os.getenv(prefix + "_MODEL_ID") or os.getenv(prefix + "_MODEL") or None,
            "endpoint": os.getenv(prefix + "_BASE_URL") or None,
            "api_key": os.getenv("AWS_BEARER_TOKEN_BEDROCK" if provider == "bedrock-runtime" else prefix + "_API_KEY") or None,
            "region": (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")) if provider == "bedrock-runtime" else None}


def configured(provider):
    options = values(provider)
    if provider == "python-runtime":
        return True
    if provider == "bedrock-runtime":
        return bool(options["model"] and options["api_key"] and options["region"])
    return bool(options["model"] and (options["api_key"] if provider == "openai-runtime" else options["endpoint"]))


def make_runtime(provider, *, model=None, timeout_s=60, max_turns=5, max_tool_calls=3, max_tokens=512):
    options = values(provider)
    options["model"] = model or options["model"]
    if provider != "python-runtime" and not options["model"]:
        raise ValueError("An explicitly configured model is required")
    if provider == "bedrock-runtime" and not options["api_key"]:
        raise ValueError("This Studio campaign requires Bedrock API key; IAM is a separate profile")
    return toolkit.runtime(provider=provider, **options, timeout_s=timeout_s, max_retries=0,
                           max_turns=max_turns, max_tool_calls=max_tool_calls,
                           max_tokens=None if provider == "python-runtime" else max_tokens)
