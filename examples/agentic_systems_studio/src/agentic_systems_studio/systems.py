"""Catalog applications expressed solely through the 2.1.3 SDK grammar."""
from dataclasses import dataclass
import json
import agentic_systems as toolkit
from .catalog import SYSTEM_SPECS, get_system_spec
from .conversation import ConversationConfig
from .operators import TOOLS


@dataclass(frozen=True)
class StudioSystem:
    spec: object
    config: ConversationConfig
    system: object

    def run(self, input=None):
        from .budget import ensure_budget
        ensure_budget()
        return self.system.run(self.spec.sample_input if input is None else input,
                               limits=toolkit.Limits(timeout_s=self.config.timeout_s * self.config.max_turns * len(self.spec.stages)))

    def inspect(self):
        return {"catalog": self.spec.to_dict(), "system": self.system.inspect()}

    def mermaid(self):
        return self.spec.mermaid(provider=self.config.provider, framework=self.config.framework)


def build_system(system_id, config):
    spec = get_system_spec(system_id)
    if config.provider == "python-runtime":
        raise ValueError("Catalog reasoners require a language-model provider; Python is not a reasoner")
    stages = []
    for stage in spec.stages:
        capability = TOOLS[stage.tool_key]
        skill = toolkit.skill(name=stage.id, tools=(capability,), instructions=stage.instructions)
        if stage.kind == "operator":
            def bind(data):
                return {"text": data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)}
            actor = toolkit.Agent(stage.id, toolkit.Action(stage.id, capability, input=bind), skills=(skill,))
        else:
            actor = toolkit.Agent(stage.id, runtime=config.reasoning_runtime(),
                framework=toolkit.framework(config.framework), skills=(skill,),
                instructions=stage.instructions + " Preserve supplied evidence and do not invent facts.",
                policy={"repair": False})
        stages.append(actor)
    return StudioSystem(spec, config, toolkit.System(spec.id, toolkit.Sequence(tuple(stages))))


def build_all(config):
    return tuple(build_system(spec.id, config) for spec in SYSTEM_SPECS)


def compose_systems(systems, *, mode="sequential"):
    steps = tuple(item.system for item in systems)
    if mode == "sequential":
        flow = toolkit.Sequence(steps)
    elif mode == "parallel":
        flow = toolkit.Parallel(steps, join=lambda branches: branches)
    else:
        raise ValueError("Choose sequential or parallel")
    return toolkit.System("studio_composition", flow)
