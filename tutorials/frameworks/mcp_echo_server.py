from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = FastMCP(
        "agentic-systems-test",
        host="127.0.0.1",
        port=args.port,
        stateless_http=True,
    )

    @server.tool()
    def echo(value: str) -> dict[str, str]:
        """Return the supplied value as local MCP evidence."""

        return {"value": value, "transport": args.transport}

    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
