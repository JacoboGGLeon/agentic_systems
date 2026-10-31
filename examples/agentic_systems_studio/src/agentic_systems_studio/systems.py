"""Catalog applications expressed solely through the 2.1.4.dev4 SDK grammar."""

from dataclasses import dataclass
import json
import agentic_systems as toolkit
from .catalog import SYSTEM_SPECS, get_system_spec
from .conversation import ConversationConfig
from .operators import TOOLS
from ._graph import pipeline
from dataclasses import replace


@dataclass(frozen=True)
class StudioSystem:
    spec: object
    config: ConversationConfig
    system: object

    def run(self, input=None):
        from .budget import ensure_budget

        ensure_budget()
        result = self.system.run(
            {"payload": self.spec.sample_input if input is None else input},
            timeout_s=self.config.timeout_s
                * self.config.max_turns
                * len(self.spec.stages),
        )
        return replace(result, data=result.data.get("payload", {}))

    def inspect(self):
        return {"catalog": self.spec.to_dict(), "system": self.system.inspect()}

    def mermaid(self):
        return self.spec.mermaid(
            provider=self.config.provider, framework=self.config.framework
        )


def build_system(system_id, config):
    spec = get_system_spec(system_id)
    if config.provider == "python-runtime":
        raise ValueError(
            "Catalog reasoners require a language-model provider; Python is not a reasoner"
        )
    stages = []
    for stage in spec.stages:
        capability = TOOLS[stage.tool_key]
        skill = toolkit.skill(
            name=stage.id, tools=(capability,), instructions=stage.instructions
        )
        if stage.kind == "operator":

            def bind(data):
                return {
                    "text": data
                    if isinstance(data, str)
                    else json.dumps(data, ensure_ascii=False)
                }

            def actor(data, tool=capability):
                return tool.run(bind(data))
        else:
            actor = toolkit.Agent(
                stage.id,
                runtime=config.reasoning_runtime(),
                framework=toolkit.framework(config.framework),
                skills=(skill,),
                instructions=stage.instructions
                + " Preserve supplied evidence and do not invent facts.",
                policy={"repair": False},
            )
        stages.append(actor)
    return StudioSystem(spec, config, pipeline(spec.id, tuple(stages)))


def build_all(config):
    return tuple(build_system(spec.id, config) for spec in SYSTEM_SPECS)


def compose_systems(systems, *, mode="sequential"):
    steps = tuple(item.system for item in systems)
    if mode == "sequential":

        def stage(app):
            def execute(data):
                raw = app.run({"payload": data})
                return replace(raw, data=raw.data.get("payload", raw.data))

            return execute

        return pipeline("studio_composition", tuple(stage(app) for app in steps))
    if mode != "parallel":
        raise ValueError("Choose sequential or parallel")
    from typing import Annotated
    import pydantic

    def merge(left, right):
        if left.keys() & right.keys():
            raise ValueError("Duplicate system identities")
        return {**left, **right}

    class State(pydantic.BaseModel):
        payload: dict
        results: Annotated[dict, merge] = pydantic.Field(default_factory=dict)

    graph = toolkit.Graph(State)
    for index, app in enumerate(steps):
        name = "system_" + str(index)

        def node(state, app=app, name=name):
            raw = app.run({"payload": state.payload})
            return replace(
                raw, data={"results": {name: raw.data.get("payload", raw.data)}}
            )

        graph.add_node(name, node)
        graph.add_edge(toolkit.START, name)
        graph.add_edge(name, toolkit.END)
    return toolkit.System("studio_parallel", graph=graph)
