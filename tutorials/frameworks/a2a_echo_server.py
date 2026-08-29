"""Local A2A server used by the Strands framework tutorial.

The server deliberately uses ``python-runtime`` so the protocol boundary can
be exercised offline. Strands owns the A2A server and Agentic Systems owns the
deterministic Tool contract exposed by the remote agent.
"""

from __future__ import annotations

import argparse

from strands.multiagent.a2a import A2AServer

import agentic_systems as toolkit


def _agent_factory(context_id: str):
    @toolkit.tool
    def echo(value: str) -> dict[str, object]:
        return {
            "value": value,
            "transport": "a2a",
            "context_isolated": bool(context_id),
        }

    remote_agent = toolkit.agent(
        name="agentic_systems_a2a_echo",
        instructions="Execute the requested echo Tool.",
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(
            "strands",
            agent_kwargs={
                "description": "Deterministic A2A echo agent for transport validation."
            },
        ),
        tools=[echo],
    )
    remote_agent.prepare()
    return remote_agent.native_agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    server = A2AServer(
        agent_factory=_agent_factory,
        host=args.host,
        port=args.port,
        version=toolkit.__version__,
    )
    server.serve()


if __name__ == "__main__":
    main()
