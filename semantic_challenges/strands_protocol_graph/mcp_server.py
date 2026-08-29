"""Local stdio MCP server for the protocol challenge."""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    bound_token = str(args.token).strip()
    if not bound_token:
        raise ValueError("The MCP evidence binding cannot be empty.")
    server = FastMCP("agentic-systems-semantic-challenge")

    @server.tool()
    def fetch_mcp_evidence() -> dict[str, str]:
        """Return the evidence authorized for this isolated MCP session."""

        return {"protocol": "mcp", "token": bound_token, "status": "verified"}

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
