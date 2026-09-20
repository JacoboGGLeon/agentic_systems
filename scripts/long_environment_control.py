"""Deterministic topology control; never a substitute for semantic inference."""

import copy
import agentic_systems as toolkit
from agentic_systems.execution import SequentialPlan

SPEC = {
    "steps": 7,
    "agents": 9,
    "tools": 11,
    "skills": 5,
    "role": "deterministic-control",
    "groups": [[0, 1], [2, 3], [4], [5], [6], [7], [8], [9], [10]],
}


def build_control(
    framework="native", *, fail_step=None, final_provider="python-runtime", model=None
):
    observed = []
    runs = []
    runtime = toolkit.runtime(provider="python-runtime")
    system = toolkit.system(runtime=runtime)

    def make_tool(index):
        def operation(value: int, step: int) -> dict:
            failed = step == fail_step and index == 5
            observed.append(
                {
                    "name": f"operation_{index}",
                    "value": value,
                    "step": step,
                    "ok": not failed,
                }
            )
            if failed:
                raise ValueError("injected_operation_failure")
            return {"value": value + index + 1}

        return toolkit.tool(name=f"operation_{index}")(operation)

    tools = [make_tool(index) for index in range(SPEC["tools"])]
    skill_groups = [
        [item for group in SPEC["groups"][start : start + 2] for item in group]
        for start in range(0, SPEC["agents"], 2)
    ]
    skills = [
        toolkit.skill(name=f"capability_{index}", tools=[tools[item] for item in group])
        for index, group in enumerate(skill_groups)
    ]
    # Register the five real capability packages, then choose each actor's subset.
    for skill in skills:
        system.skill(skill)
    for index, group in enumerate(SPEC["groups"]):
        selected = (
            runtime
            if index != SPEC["agents"] - 1
            else toolkit.runtime(
                provider=final_provider,
                model=model,
                scheduler=toolkit.scheduler(max_retries=0, timeout_s=120),
            )
        )
        system.agent(
            name=f"operator_{index}",
            instructions="Execute the explicit tool plan.",
            skills=[skills[index // 2]],
            framework=framework,
            runtime=selected,
            policy=toolkit.RunPolicy(
                max_tokens=700, max_turns=3, max_tool_calls=len(group)
            ),
        )
    state = {}

    def request(group):
        return {
            "steps": [
                {
                    "tool": f"operation_{index}",
                    "input": {"value": state["value"], "step": state["step"]},
                }
                for index in group
            ]
        }

    def select(result):
        events = result.normalized()["tools"]
        state["value"] = (
            sum(event["output"]["value"] for event in events)
            - (len(events) - 1) * state["value"]
        )
        state["actor"] += 1
        return (
            request(SPEC["groups"][state["actor"]])
            if state["actor"] < SPEC["agents"]
            else {"value": state["value"]}
        )

    system.inspect().raise_if_errors()
    executable = system.compile(
        name="long-control", execution=SequentialPlan(input_selector=select)
    )

    def transition(row, action, info):
        state.update(value=info["memory"].get("value", 0), step=row["step"], actor=0)
        result = executable.run(request(SPEC["groups"][0]))
        runs.append(result)
        return {
            "run": result.normalized(),
            "lineage": result.lineage().model_dump(mode="json"),
            "memory": {
                "value": state["value"] if result.ok else info["memory"].get("value", 0)
            },
            "ok": result.ok,
        }

    env = toolkit.environment(
        records=[{"step": index} for index in range(SPEC["steps"])],
        transition_fn=transition,
        initial_memory={"value": 0},
    )
    return env, observed, runs


def run_episode(env):
    env.reset(seed=19)
    while True:
        _, _, terminated, truncated, _ = env.step()
        if terminated or truncated:
            break
    return copy.deepcopy([entry.to_dict() for entry in env.history])
