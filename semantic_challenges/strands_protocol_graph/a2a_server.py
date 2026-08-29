"""Local A2A server backed by an Agentic Systems deterministic Agent."""

from __future__ import annotations

import argparse

from strands.multiagent.a2a import A2AServer

import agentic_systems as toolkit


def _agent_factory(context_id: str):
    @toolkit.tool
    def fetch_remote_evidence(token: str) -> dict[str, object]:
        return {
            "protocol": "a2a",
            "token": token,
            "status": "verified",
            "context_isolated": bool(context_id),
        }

    remote = toolkit.agent(
        name="protocol_evidence_agent",
        instructions="Execute fetch_remote_evidence exactly once.",
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(
            "strands",
            agent_kwargs={"description": "Deterministic remote A2A evidence Agent."},
        ),
        tools=[fetch_remote_evidence],
    )
    remote.prepare()
    return remote.native_agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    A2AServer(
        agent_factory=_agent_factory,
        host=args.host,
        port=args.port,
        version=toolkit.__version__,
    ).serve()


if __name__ == "__main__":
    main()
