"""Executable assembly for Incident Response."""

import os
import agentic_systems as toolkit
from .tools import normalize_input, record_note

STAGES = [{'id': 'triage', 'name': 'Triage operator', 'kind': 'operator', 'instructions': 'Score only visible incident signals and timestamps.'}, {'id': 'command', 'name': 'Incident commander', 'kind': 'reasoner', 'instructions': 'Set priorities, owners and stop conditions.'}, {'id': 'diagnose', 'name': 'Diagnosis agent', 'kind': 'reasoner', 'instructions': 'Rank hypotheses and request discriminating evidence.'}, {'id': 'remediate', 'name': 'Remediation agent', 'kind': 'reasoner', 'instructions': 'Propose reversible mitigation and validation steps.'}, {'id': 'review', 'name': 'Safety reviewer', 'kind': 'reviewer', 'instructions': 'Reject unsafe certainty and return an action plan.'}]


def build_system():
    provider = os.getenv("AGENTIC_PROVIDER", "openai-runtime")
    framework = os.getenv("AGENTIC_FRAMEWORK", "agentic-systems")
    model = os.getenv("AGENTIC_MODEL") or None
    runtime = toolkit.runtime(provider=provider, model=model)
    system = toolkit.system(runtime=runtime, model=model)

    for stage in STAGES:
        operator = stage["kind"] == "operator"
        tool = normalize_input if operator else record_note
        skill = toolkit.skill(
            name=f"safe-incident-response-{stage['id']}",
            description=stage["instructions"],
            tools=[tool],
            version="2.0.0",
        )
        system.agent(
            name=f"incident-response.{stage['id']}",
            instructions=stage["instructions"],
            skills=[skill],
            engine="python-runtime" if operator else provider,
            framework=None if operator or framework == "agentic-systems" else framework,
            model=None if operator else model,
            runtime=toolkit.runtime(provider="python-runtime") if operator else runtime,
            policy={"max_tokens": 1024, "max_turns": 6, "max_tool_calls": 4},
        )

    report = system.inspect()
    report.raise_if_errors()
    return system.compile(execution=toolkit.SequentialPlan(), name="incident-response")
