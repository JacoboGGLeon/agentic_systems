"""Executable assembly for Research Synthesis."""

import os
import agentic_systems as toolkit
from .tools import normalize_input, record_note

STAGES = [{'id': 'extract', 'name': 'Evidence operator', 'kind': 'operator', 'instructions': 'Extract claims, links, figures and uncertainty.'}, {'id': 'synthesize', 'name': 'Research synthesizer', 'kind': 'reasoner', 'instructions': 'Synthesize only extracted evidence and retain uncertainty.'}, {'id': 'critic', 'name': 'Adversarial critic', 'kind': 'reasoner', 'instructions': 'Find contradictions, missing evidence and overclaiming.'}, {'id': 'review', 'name': 'Research editor', 'kind': 'reviewer', 'instructions': 'Produce the evidence-qualified synthesis.'}]


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
            name=f"evidence-grounded-synthesis-{stage['id']}",
            description=stage["instructions"],
            tools=[tool],
            version="2.0.0",
        )
        system.agent(
            name=f"research-synthesis.{stage['id']}",
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
    return system.compile(execution=toolkit.SequentialPlan(), name="research-synthesis")
