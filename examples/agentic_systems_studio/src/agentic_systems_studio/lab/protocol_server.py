"""Loopback-only MCP/A2A services; neither service has a language-model provider."""
import argparse
import sys
from pathlib import Path


def local_only():
    def guard(event, args):
        if event == "socket.connect":
            address = args[1]
            if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
                raise RuntimeError("The protocol fixture permits only loopback")
        if event == "socket.getaddrinfo" and args[0] not in {"127.0.0.1", "::1", "localhost", None}:
            raise RuntimeError("External DNS is forbidden in protocol fixtures")
    sys.addaudithook(guard)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("mcp", "a2a"))
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    local_only()
    if args.kind == "mcp":
        from mcp.server.fastmcp import FastMCP
        server = FastMCP("local-evidence", host="127.0.0.1", port=args.port, stateless_http=True)

        @server.tool()
        def echo(value: str) -> dict:
            """Return the value with evidence of an actual MCP transport."""
            return {"value": value, "transport": "mcp-streamable-http"}
        server.run(transport="streamable-http")
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from native_profiles import strands_fixture_model
        from strands import Agent, tool
        from strands.multiagent.a2a import A2AServer

        @tool
        def echo(value: str) -> dict:
            return {"value": value, "transport": "a2a"}

        def factory(context_id):
            return Agent(name="agentic_systems_a2a_echo", model=strands_fixture_model(), tools=[echo],
                         description="Deterministic isolated A2A agent", callback_handler=None)
        A2AServer(agent_factory=factory, host="127.0.0.1", port=args.port, version="2.1.3").serve()


if __name__ == "__main__":
    main()
