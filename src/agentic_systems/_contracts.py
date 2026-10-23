"""Closed user dictionaries; the engine's policy vocabulary remains private."""
from __future__ import annotations

from dataclasses import replace
import json

from ._results import _from_engine, _json


def _closed(value, allowed, label):
    if value is None:
        return {}
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(label + " accepts only: " + ", ".join(sorted(allowed)))
    return _json(value)


def _validate_schema(schema):
    from jsonschema import Draft202012Validator
    if not isinstance(schema, dict):
        raise TypeError("output_schema must be a JSON Schema dictionary")
    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value and not value["$ref"].startswith("#"):
                raise ValueError("Schema references must be local; no remote resolution")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(schema)
    Draft202012Validator.check_schema(schema)
    return _json(schema)


def _validate_contract(value, tools=(), runtime=None):
    result = _closed(value, {"tool_expectation", "completion", "failure_policy", "expected_output", "expected_tool_outputs", "output_schema"}, "contract")
    expectation = _closed(result.get("tool_expectation"), {"all_of", "any_of", "allowed", "forbidden", "min_count"}, "tool_expectation")
    for key in ("all_of", "any_of", "allowed", "forbidden"):
        if key in expectation and (not isinstance(expectation[key], list) or any(not isinstance(v, str) for v in expectation[key])):
            raise TypeError(key + " requires a list of Tool names")
    references = set().union(*(set(expectation.get(k, [])) for k in ("all_of", "any_of", "allowed", "forbidden")))
    if references - set(tools):
        raise ValueError("Contract references unavailable Tools")
    required, forbidden = set(expectation.get("all_of", [])), set(expectation.get("forbidden", []))
    allowed = set(expectation["allowed"]) if "allowed" in expectation else set(tools)
    if required & forbidden or required - allowed:
        raise ValueError("Contradictory required/allowed/forbidden Tools")
    if expectation.get("any_of") and not set(expectation["any_of"]) & (allowed - forbidden):
        raise ValueError("No any_of Tool can satisfy this contract")
    if "min_count" in expectation:
        count = expectation["min_count"]
        if type(count) is not int or count < 0:
            raise ValueError("min_count must be nonnegative")
        if runtime and count > runtime.max_tool_calls:
            raise ValueError("Contract exceeds the actor Tool budget")
    if runtime and len(required) > runtime.max_tool_calls:
        raise ValueError("Required Tools exceed the actor budget")
    if result.get("completion", "default") not in {"default", "when_required_tools_satisfied", "always_finalize"}:
        raise ValueError("Unknown exact completion mode")
    if result.get("failure_policy", "no_unresolved") not in {"allow", "no_unresolved", "fail_fast"}:
        raise ValueError("Unknown exact failure_policy")
    for key in ("expected_output", "expected_tool_outputs"):
        if key in result and not isinstance(result[key], dict):
            raise TypeError(key + " must be a dictionary")
    outputs = result.get("expected_tool_outputs", {})
    if set(outputs) - set(tools) or any(not isinstance(v, dict) for v in outputs.values()):
        raise ValueError("expected_tool_outputs requires available Tool names and dictionary expectations")
    if "output_schema" in result:
        result["output_schema"] = _validate_schema(result["output_schema"])
    if expectation:
        result["tool_expectation"] = expectation
    return result


def _validate_policy(value):
    result = _closed(value, {"temperature", "tool_choice", "repair", "max_repairs", "finalize", "trace", "strict"}, "policy")
    if "temperature" in result and (type(result["temperature"]) not in {int, float} or not 0 <= result["temperature"] <= 2):
        raise ValueError("temperature must be between 0 and 2")
    if "max_repairs" in result and (type(result["max_repairs"]) is not int or result["max_repairs"] < 0):
        raise ValueError("max_repairs must be nonnegative")
    for key in ("repair", "strict"):
        if key in result and type(result[key]) is not bool:
            raise TypeError(key + " must be boolean")
    for key, allowed in (("tool_choice", {"auto", "required", "none"}), ("trace", {"compact", "full"}),
                         ("finalize", {"never", "on_max_turns", "after_required_tools"})):
        if key in result and result[key] not in allowed:
            raise ValueError("Unknown " + key)
    return result


def _invoke_actor(owner, config, selected_framework, contract, policy, value):
    from ._engine.factories import agent
    expectation = contract.get("tool_expectation", {})
    private_contract = {k: v for k, v in contract.items() if k != "output_schema"}
    if expectation:
        private_contract["tool_expectation"] = {k: v for k, v in expectation.items() if k != "forbidden"}
        private_contract["must_call"] = expectation.get("all_of", [])
        private_contract["must_not_call"] = expectation.get("forbidden", [])
    private_contract["require_no_unresolved_tool_failures"] = contract.get("failure_policy") != "allow"
    private_policy = {**policy, "max_turns": config.max_turns, "max_tool_calls": config.max_tool_calls}
    if config.max_tokens is not None:
        private_policy["max_tokens"] = config.max_tokens
    instructions = owner.instructions
    if "output_schema" in contract:
        instructions += "\nReturn a JSON object satisfying this JSON Schema: " + json.dumps(contract["output_schema"])
    actor = agent(name=owner.name, runtime=config._to_engine(), framework=selected_framework._to_engine(),
                  skills=[s._to_engine() for s in owner.skills], instructions=instructions,
                  contract=private_contract, policy=private_policy)
    return _from_engine(actor.run(value))


def _check_output(output, contract):
    issues = []
    schema = contract.get("output_schema")
    if schema is not None:
        from jsonschema import Draft202012Validator
        data = output.data
        if not data and output.text:
            try:
                data = json.loads(output.text)
            except (TypeError, ValueError):
                issues.append({"code": "invalid_structured_output", "message": "Model text is not JSON"})
        if isinstance(data, dict):
            for error in Draft202012Validator(schema).iter_errors(data):
                issues.append({"code": "output_schema_mismatch", "message": error.message, "path": list(error.path)})
        else:
            issues.append({"code": "output_schema_mismatch", "message": "Expected a JSON object"})
        if not issues:
            output = replace(output, data=data)
    called = {e.name for n in output.walk() for e in n.tool_events}
    forbidden = set(contract.get("tool_expectation", {}).get("forbidden", []))
    if called & forbidden:
        issues.append({"code": "forbidden_tool", "message": "Observed a forbidden Tool"})
    if issues:
        return replace(output, ok=False, errors=(*output.errors, *issues), validation={"ok": False, "issues": issues})
    if output.ok and contract.get("failure_policy") == "allow":
        output = replace(output, meta={**output.meta, "allowed_error_ids": [n.execution_id for n in output.walk()]})
    return output
