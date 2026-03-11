"""Operator connection tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..td_client import td


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def td_connect(
        from_op: str,
        to_op: str,
        from_index: int = 0,
        to_index: int = 0,
    ) -> dict:
        """Connect two operators.

        Args:
            from_op: Source operator path
            to_op: Destination operator path
            from_index: Output connector index on source (default 0)
            to_index: Input connector index on destination (default 0)
        """
        return await td.request("connect", {
            "from_op": from_op,
            "to_op": to_op,
            "from_index": from_index,
            "to_index": to_index,
        })

    @mcp.tool()
    async def td_disconnect(
        path: str,
        connector: str = "input",
        index: int = 0,
    ) -> dict:
        """Disconnect an operator's connector.

        Args:
            path: Operator path
            connector: "input" or "output" (default "input")
            index: Connector index (default 0)
        """
        return await td.request("disconnect", {
            "path": path,
            "connector": connector,
            "index": index,
        })
