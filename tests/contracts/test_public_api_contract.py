from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import sys

import agentic_systems
import agentic_systems.providers as providers
import agentic_systems.providers.bedrock_runtime as bedrock_runtime


EXPECTED_BEDROCK_RUNTIME_SIGNATURES = {
    "__init__": "(self, *, model_id: 'str', region_name: 'Optional[str]' = None, max_tokens_default: 'int' = 800, temperature_default: 'float' = 0.0, logger_name: 'str' = 'agentic_systems') -> 'None'",
    "whoami": "(self, *, mask: 'bool' = False) -> 'Dict[str, Any]'",
    "redact_aws_identity": "(identity: 'Dict[str, Any]') -> 'Dict[str, Any]'",
    "model_availability": "(self, model_id: 'Optional[str]' = None, *, full_metadata: 'bool' = True) -> 'Dict[str, Any]'",
    "tool": "(self, func: 'Optional[Callable[..., Any]]' = None, *, name: 'Optional[str]' = None, description: 'Optional[str]' = None)",
    "export_tool_specs": "(self, tool_names: 'Optional[Sequence[str]]' = None) -> 'List[Dict[str, Any]]'",
    "print_tool_specs": "(self) -> 'None'",
    "validate_tool_registry": "(self, tool_names: 'Optional[Sequence[str]]' = None) -> 'Dict[str, Any]'",
    "to_envelope": "(value: 'Any', *, tool_name: 'str', ok: 'bool' = True, extra_meta: 'Optional[Dict[str, Any]]' = None) -> 'ToolEnvelope'",
    "dumps_tool_output": "(value: 'Any', *, tool_name: 'str', ok: 'bool' = True, extra_meta: 'Optional[Dict[str, Any]]' = None) -> 'str'",
    "parse_tool_output": "(raw: 'Any') -> 'Dict[str, Any]'",
    "parse_framework_tool_output": "(raw: 'Any', *, expected_tool_name: 'Optional[str]' = None) -> 'Dict[str, Any]'",
    "execute_tool": "(self, tool_name: 'str', tool_input: 'Optional[Dict[str, Any]]' = None) -> 'ToolEnvelope'",
    "converse": "(self, *, messages: 'List[Dict[str, Any]]', system: 'Optional[List[Dict[str, str]]]' = None, tools: 'Optional[List[Dict[str, Any]]]' = None, tool_choice: 'Optional[Dict[str, Any]]' = None, model_id: 'Optional[str]' = None, max_tokens: 'Optional[int]' = None, temperature: 'Optional[float]' = None, top_p: 'Optional[float]' = None, stop_sequences: 'Optional[List[str]]' = None) -> 'Dict[str, Any]'",
    "bedrock_safe_tool_name": "(name: 'str') -> 'str'",
    "as_bedrock_tools": "(self, tool_names: 'Optional[Sequence[str]]' = None, *, canonical_to_bedrock: 'Optional[Dict[str, str]]' = None) -> 'List[Dict[str, Any]]'",
    "run_direct": "(self, prompt: 'str', *, instructions: 'Optional[str]' = None, model_id: 'Optional[str]' = None, tool_choice: 'Optional[str]' = 'auto', tool_names: 'Optional[Sequence[str]]' = None, max_turns: 'int' = 8, max_tool_calls: 'Optional[int]' = None, max_tokens: 'Optional[int]' = None, temperature: 'Optional[float]' = None, retry_tool_errors: 'bool' = True, max_tool_error_repairs: 'int' = 2, synthesize_final_on_max_turns: 'bool' = True, required_tools: 'Optional[Sequence[str]]' = None, stop_when_required_tools_ok: 'bool' = False) -> 'BedrockRunResult'",
    "print_run_result": "(result: 'BedrockRunResult', *, mode: 'str' = 'compact') -> 'None'",
    "as_langgraph_node": "(self, *, instructions: 'Optional[str]' = None, tool_choice: 'Optional[str]' = 'auto', tool_names: 'Optional[Sequence[str]]' = None, max_turns: 'int' = 8, max_tool_calls: 'Optional[int]' = None, max_tokens: 'Optional[int]' = None, temperature: 'Optional[float]' = None, retry_tool_errors: 'bool' = True, max_tool_error_repairs: 'int' = 2, synthesize_final_on_max_turns: 'bool' = True, required_tools: 'Optional[Sequence[str]]' = None, stop_when_required_tools_ok: 'bool' = False, input_key: 'str' = 'prompt', output_key: 'str' = 'final_text', trace_key: 'str' = 'ada_trace', trace_mode: 'str' = 'compact') -> 'Callable[[Dict[str, Any]], Dict[str, Any]]'",
}


def test_public_api_and_bedrock_exports_are_frozen_for_2_1():
    assert len(agentic_systems.__all__) == 87
    assert providers.BedrockRuntime is bedrock_runtime.BedrockRuntime
    assert providers.BedrockRunResult is bedrock_runtime.BedrockRunResult
    assert not hasattr(bedrock_runtime, "__version__")
    assert providers.RuntimeToolCallRecord is bedrock_runtime.RuntimeToolCallRecord
    for name in (
        "ToolEnvelope",
        "RuntimeToolSpec",
        "RuntimeToolCallRecord",
        "BedrockRunResult",
        "BedrockRuntime",
    ):
        assert hasattr(bedrock_runtime, name)


def test_bedrock_runtime_public_signatures_are_frozen_for_2_0():
    public_method_names = {
        name
        for name, value in inspect.getmembers(bedrock_runtime.BedrockRuntime)
        if callable(value) and (name == "__init__" or not name.startswith("_"))
    }
    assert public_method_names == set(EXPECTED_BEDROCK_RUNTIME_SIGNATURES)

    actual = {
        name: str(inspect.signature(getattr(bedrock_runtime.BedrockRuntime, name)))
        for name in public_method_names
    }
    assert actual == EXPECTED_BEDROCK_RUNTIME_SIGNATURES


def test_minimal_import_does_not_eagerly_load_optional_providers():
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import agentic_systems, sys; "
            "assert 'boto3' not in sys.modules; "
            "assert 'langgraph' not in sys.modules; "
            "assert 'openai' not in sys.modules; "
            "assert 'agents' not in sys.modules; "
            "assert 'strands' not in sys.modules",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
