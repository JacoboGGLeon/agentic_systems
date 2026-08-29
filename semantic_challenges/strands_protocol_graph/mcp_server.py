"""Local stdio MCP server for the protocol challenge."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def main() -> None:
    server = FastMCP("agentic-systems-semantic-challenge")

    @server.tool()
    def fetch_mcp_evidence(token: str) -> dict[str, str]:
        """Return the token as evidence produced across the MCP boundary."""

        return {"protocol": "mcp", "token": token, "status": "verified"}

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
