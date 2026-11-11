"""Execute the revised README blocks; simulate only Bedrock's transport."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
from importlib import metadata
import io
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / ".tmp/readme-validation"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "tutorials"))
from _offline import enforce_offline, blocked_attempts

enforce_offline()
from botocore.client import BaseClient

markdown = (REPO / "README.md").read_text()
blocks = re.findall(r"```python\n(.*?)\n```", markdown, re.S)
model_block = next(block for block in blocks if "runtime = toolkit.runtime(" in block)
switch_block = next(block for block in blocks if "other_assistant = toolkit.Agent(" in block)
local_blocks = [block for block in blocks if block not in (model_block, switch_block)]
local_code = "\n\n".join(local_blocks)
(OUT / "readme_local.py").write_text(local_code + "\n")
namespace = {}
output = io.StringIO()
responses = []


def simulated_converse(self, operation, params):
    assert operation == "Converse", operation
    user_text = [block["text"] for message in params["messages"]
                 if message["role"] == "user" for block in message["content"] if "text" in block]
    question = user_text[-1]
    tool = "read_runbook" if "guidance" in question.lower() else "inspect_service"
    has_result = any("toolResult" in block for message in params["messages"] for block in message["content"])
    responses.append({"operation": operation, "tool": tool})
    content = [{"text": "Completed using the requested Tool."}] if has_result else [{"toolUse": {
        "toolUseId": "call-" + str(len(responses)), "name": tool, "input": {"service": "checkout"},
    }}]
    return {"output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "end_turn" if has_result else "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "metrics": {"latencyMs": 1}, "ResponseMetadata": {"HTTPStatusCode": 200}}


def check_result(result):
    executions = list(result.walk())
    assert len(executions) == len({execution.execution_id for execution in executions})
    for execution in executions:
        assert execution.check_invariants().ok, execution.check_invariants().to_dict()


evidence = {}
with redirect_stdout(output), redirect_stderr(output):
    exec(compile(local_code, "README:local", "exec"), namespace)
    toolkit = namespace["toolkit"]
    local_results = {name: value for name, value in namespace.items() if isinstance(value, toolkit.RunResult)}
    for result in local_results.values():
        check_result(result)
    assert len(namespace["episodes"].data["outputs"]) == 2
    assert not namespace["negative_control"].run().ok
    healthy = namespace["system"].run({"service": "catalog"})
    failed = namespace["system"].run({"service": "unknown"})
    assert healthy.ok and healthy.data["action"] == "monitor"
    assert not failed.ok
    for result in (healthy, failed):
        check_result(result)
    evidence["local"] = {name: result.evidence() for name, result in local_results.items()}
    evidence["healthy_branch"] = healthy.evidence()
    evidence["unknown_service"] = failed.evidence()
    config = {"AWS_REGION": "us-east-1", "BEDROCK_MODEL_ID": "qwen.qwen3-32b-v1:0",
              "AWS_ACCESS_KEY_ID": "offline-placeholder", "AWS_SECRET_ACCESS_KEY": "offline-placeholder",
              "AWS_EC2_METADATA_DISABLED": "true"}
    with patch.dict(os.environ, config), patch.object(BaseClient, "_make_api_call", simulated_converse):
        exec(compile(model_block + "\n\n" + switch_block, "README:models", "exec"), namespace)
        for actor_name, result_name in [("assistant", "model_result"), ("other_assistant", "other_result")]:
            actor = namespace[actor_name]
            for label, result, expected in [
                ("guidance", namespace[result_name], "read_runbook"),
                ("health", actor.run("What is the current health of checkout?"), "inspect_service"),
            ]:
                assert result.ok, result.evidence()
                calls = [event for run in result.walk() for event in run.tool_events]
                assert len(calls) == 1 and calls[0].ok and calls[0].name == expected
                assert calls[0].input == {"service": "checkout"}
                check_result(result)
                evidence[actor_name + "/" + label] = result.evidence()

    # Verify documentation targets against this checkout; no HTTP requests.
    prefix = "https://github.com/JacoboGGLeon/agentic_systems/"
    for target in re.findall(r"\]\(([^)]+)\)", markdown):
        if target.startswith(prefix + "blob/main/") or target.startswith(prefix + "tree/main/"):
            assert (REPO / target.split("/main/", 1)[1]).exists(), target
        elif "://" not in target and not target.startswith("#"):
            assert (REPO / target).exists(), target

assert blocked_attempts() == 0
report = {"sdk_version": metadata.version("agentic-systems"), "python": sys.version.split()[0],
          "readme_sha256": hashlib.sha256(markdown.encode()).hexdigest(),
          "first_example_lines": len(local_blocks[0].splitlines()),
          "python_blocks_executed": len(blocks), "local_blocks": len(local_blocks),
          "checks": {"local_capability": "PASS", "accepting_eval": "PASS", "negative_control": "PASS",
                     "conditional_system_branches": "PASS", "unknown_service_failure": "PASS",
                     "environment_stop": "PASS", "compiled_system": "PASS",
                     "bedrock_native_simulated_two_tools": "PASS", "openai_agents_simulated_two_tools": "PASS",
                     "result_invariants": "PASS", "link_targets_in_checkout": "PASS"},
          "simulated_converse_calls": len(responses), "real_bedrock_requests": 0,
          "blocked_network_attempts": blocked_attempts(), "live_inference": "NOT RUN",
          "diagram_browser_rendering": "NOT RUN", "acceptance": "PASS"}
(OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
(OUT / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
(OUT / "execution.log").write_text(output.getvalue())
print(json.dumps(report, indent=2))
