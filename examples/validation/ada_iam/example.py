"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

import os


def run():
    runtime = toolkit.runtime(provider='bedrock-runtime', model=os.getenv("VLLM_MODEL" if 'bedrock-runtime' == "vllm-runtime" else "BEDROCK_MODEL_ID") or "configure-in-target-environment",
        **({"endpoint": os.getenv("VLLM_BASE_URL") or "http://127.0.0.1:8000/v1"} if 'bedrock-runtime' == "vllm-runtime" else {"region": os.getenv("AWS_REGION") or "us-east-2"}))
    actor = toolkit.Agent("target", runtime=runtime, instructions="Use the supplied evidence.")
    return {"mode": 'ADA workload IAM', "runtime": runtime.inspect(), "application": actor.inspect(),
            "status": "configuration-only; target environment not executed", "inference_requests": 0,
            "authentication": "Remove bearer token from the target IAM process; use its workload role. Never embed access keys."}
